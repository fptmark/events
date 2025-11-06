# app/services/auth/cookies/redis.py
from typing import Optional, Dict, Any
import uuid
import json
import time
import redis.asyncio as redis
from fastapi import Request, Response
from pydantic import BaseModel
from app.services.framework import decorators
from app.core.metadata import MetadataService
from app.core.notify import Notification
from app.services.services import ServiceManager

# Request/Response models
class AuthResponse(BaseModel):
    """Standard authn response"""
    success: bool
    message: str | None = None

# Configuration constants – these could be loaded from config.json later.
SESSION_TTL = 3600              # 1 hour sliding window
ABSOLUTE_SESSION_MAX = 28800    # 8 hours absolute maximum (force re-login)
NEAR_EXPIRY_THRESHOLD = 300     # 5 minutes threshold

# --- Concrete Cookie Store Implementation Using Async Redis ---
class RedisCookieStore:
    def __init__(self, host: str = "127.0.0.1", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self.redis_client = None

    async def connect(self):
        self.redis_client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            encoding="utf-8",
            decode_responses=True
        )

    async def set_session(self, session_id: str, session_data: dict, ttl: int) -> None:
        if self.redis_client is None:
            raise RuntimeError("Redis client not connected")
        await self.redis_client.setex(session_id, ttl, json.dumps(session_data))

    async def get_session(self, session_id: str) -> dict:
        if self.redis_client is None:
            raise RuntimeError("Redis client not connected")
        session_json = await self.redis_client.get(session_id)
        if session_json is None:
            return {}
        try:
            return json.loads(session_json)
        except Exception:
            return {}

    async def delete_session(self, session_id: str) -> None:
        if self.redis_client is None:
            raise RuntimeError("Redis client not connected")
        await self.redis_client.delete(session_id)

    async def get_session_ttl(self, session_id: str) -> int:
        """Get remaining TTL for session key in seconds. Returns -1 if key doesn't exist."""
        if self.redis_client is None:
            raise RuntimeError("Redis client not connected")
        return await self.redis_client.ttl(session_id)

    async def renew_session(self, session_id: str, session_data: dict, ttl: int) -> dict:
        if self.redis_client is None:
            raise RuntimeError("Redis client not connected")
        await self.redis_client.setex(session_id, ttl, json.dumps(session_data))
        return session_data

# --- Auth Service Implementation Using Cookies + Redis ---
@decorators.service_config(
    entity=True,
    inputs={"login": str, "password": str},
    outputs=["roleId"]
)
class Authn:
    # Default cookie configuration; can be overridden via config.
    cookie_name = "sessionId"
    cookie_options = {
        "httponly": True,
        "secure": True,    # For local development, you might set this to False if not using HTTPS.
        "samesite": "lax"
    }
    # The backing store will be set via the asynchronous initialize() class method.
    cookie_store: Optional[RedisCookieStore] = None
    # Service configuration (entity and field mappings)
    service_config: Optional[dict] = None

    @classmethod
    async def initialize(cls, config: dict):
        """
        Initialize the authn service using settings from config.
        Expected config keys: host, port, db (for Redis), entity, fields, etc.
        """
        store = RedisCookieStore(
            host=config.get("host", "127.0.0.1"),
            port=config.get("port", 6379),
            db=config.get("db", 0)
        )
        await store.connect()
        cls.cookie_store = store
        cls.service_config = config
        print(f"  Authn service configured for entity: {config.get('entity', 'Missing')}")
        return cls

    @classmethod
    async def authorized(cls) -> Optional[dict]:
        """
        Check if current request has valid session.
        Called by GatingService to validate authentication.

        Handles session management:
        - Checks absolute expiry (force re-login after max time)
        - Deletes expired sessions
        - Renews TTL (sliding window) for active sessions

        Returns:
            Session data dict if valid session exists, None otherwise
        """
        from app.core.request_context import RequestContext
        import time

        session_id = RequestContext.get_session_id()
        if not session_id or cls.cookie_store is None:
            return None

        session = await cls.cookie_store.get_session(session_id)
        if not session:
            return None

        # Check absolute expiry (force re-login after max time regardless of activity)
        absolute_expiry = session.get('absolute_expiry', 0)
        if time.time() > absolute_expiry:
            # Session exceeded absolute maximum - delete it
            await cls.cookie_store.delete_session(session_id)
            return None

        # Lazy TTL renewal: Only renew if TTL is below threshold (avoid Redis write on every request)
        remaining_ttl = await cls.cookie_store.get_session_ttl(session_id)
        if remaining_ttl > 0 and remaining_ttl < NEAR_EXPIRY_THRESHOLD:
            # TTL is getting low - renew the sliding window
            await cls.cookie_store.renew_session(session_id, session, SESSION_TTL)

        # Add session_id to session dict and cache in RequestContext
        session['_session_id'] = session_id
        RequestContext.set_session(session)

        return session

    @classmethod
    async def get(cls, field: str) -> Any:
        """
        Get field from current session.
        Called by RBAC to retrieve cached data (e.g., permissions).

        Args:
            field: Field name to retrieve from session

        Returns:
            Field value or None if not found
        """
        from app.core.request_context import RequestContext

        session_id = RequestContext.get_session_id()
        if not session_id or cls.cookie_store is None:
            return None

        session = await cls.cookie_store.get_session(session_id)
        if session:
            return session.get(field)
        return None

    @classmethod
    async def set(cls, field: str, value: Any) -> None:
        """
        Set field in current session.
        Called by RBAC to cache data (e.g., permissions).

        Args:
            field: Field name to set in session
            value: Value to store
        """
        from app.core.request_context import RequestContext

        session_id = RequestContext.get_session_id()
        if not session_id or cls.cookie_store is None:
            return

        session = await cls.cookie_store.get_session(session_id)
        if session:
            session[field] = value
            await cls.cookie_store.set_session(session_id, session, SESSION_TTL)

    async def authenticate(self, request: Request) -> bool:
        token = request.cookies.get(self.cookie_name)
        if not token or self.cookie_store is None:
            return False
        session = await self.cookie_store.get_session(token)
        return bool(session)

    @decorators.expose_endpoint(method="POST", route="/login", summary="Login")
    async def login(self, request: Request, response: Response) -> Dict[str, any]:
        """
        Authenticate user and create session.

        Args:
            request: FastAPI Request object
            response: FastAPI Response object for setting cookies

        Returns:
            dict with success status and message
        """
        # Extract credentials from request body
        credentials = await request.json()

        # Get entity and field mappings from service config
        if not self.service_config:
            print("ERROR: Authn service not configured properly")
            return {"success": False, "message": "Authn service not configured"}

        # Get config values using constants
        entity_name = self.service_config.get(decorators.SCHEMA_ENTITY, "")
        field_mappings = self.service_config.get(decorators.SCHEMA_INPUTS, {})

        if not entity_name:
            print("ERROR: Authn service config error - entity not specified")
            return {"success": False, "message": "Authn service entity not specified"}

        # Build input query dynamically from decorator schema
        input_query = {}
        for semantic_field in self._service_schema[decorators.SCHEMA_INPUTS].keys():
            entity_field = field_mappings.get(semantic_field)
            credential_value = credentials.get(semantic_field)

            if not entity_field or not credential_value:
                Notification.error(HTTP.UNAUTHORIZED, "Invalid credentials")
                return {"success": False, "message": "Invalid credentials"}

            input_query[entity_field] = credential_value

        if not self.cookie_store:
            Notification.error(HTTP.UNAUTHORIZED, "Invalid credentials")

        # Query database for user with EXACT match
        from app.db.factory import DatabaseFactory
        db = DatabaseFactory.get_instance()

        try:
            output = ['Id', *self.service_config.get(decorators.SCHEMA_OUTPUTS, [])]
            doc = await db.documents.bypass(entity_name, input_query, output)
        except Exception as e:
            print(f"Error during user lookup: {str(e)}")
            return {"success": False, "message": "Database error"}

        if doc is None:
            return {"success": False, "message": "Invalid credentials"}

        # Create session
        session_id = str(uuid.uuid4())
        current_time = time.time()
        session_data = {
            **doc,       # Include all returned fields from doc
            "login_value": list(input_query.values())[0],  # First credential value
            "created": current_time,
            "absolute_expiry": current_time + ABSOLUTE_SESSION_MAX  # Force re-login after absolute max
        }

        # Get permissions from authz service if running
        authz_service = ServiceManager.get_service_instance("authz")
        if authz_service:
            roleId = session_data.get('roleId')
            if roleId:
                permissions = await authz_service.permissions(roleId)
                if permissions:
                    session_data['permissions'] = permissions
                else:
                    Notification.error(HTTP.UNAUTHORIZED, "No permissions defined for role")

        await self.cookie_store.set_session(session_id, session_data, SESSION_TTL)

        # Set cookie on response
        response.set_cookie(
            key=self.cookie_name,
            value=session_id,
            **self.cookie_options
        )

        # Cache session in RequestContext for update_response (same as models do)
        from app.core.request_context import RequestContext
        session_data['_session_id'] = session_id
        RequestContext.set_session(session_data)

        # Return data through update_response (same pattern as model endpoints)
        from app.routers.endpoint_handlers import update_response
        login_data = {
            "sessionId": session_id,
            "login": session_data.get("login_value")
        }
        return await update_response(login_data)

    @decorators.expose_endpoint(method="POST", route="/logout", summary="Logout")
    async def logout(self, request: Request, response: Response) -> Dict[str, any]:
        # Set up RequestContext with session from cookie
        from app.core.request_context import RequestContext
        from app.routers.endpoint_handlers import update_response

        session_id = request.cookies.get(self.cookie_name)
        RequestContext.set_session_id(session_id)

        if session_id and self.cookie_store:
            await self.cookie_store.delete_session(session_id)
            # Delete cookie from response
            response.delete_cookie(key=self.cookie_name)
            # Return through update_response (no session, so no permissions)
            return await update_response({"logout": "successful"})

        # No session - return error via Notification
        Notification.error(HTTP.UNAUTHORIZED, "No active session")

    @decorators.expose_endpoint(method="POST", route="/refresh", summary="Refresh session")
    async def refresh(self, request: Request, response: Response) -> Dict[str, any]:
        # Set up RequestContext with session from cookie
        from app.core.request_context import RequestContext
        from app.routers.endpoint_handlers import update_response

        session_id = request.cookies.get(self.cookie_name)
        RequestContext.set_session_id(session_id)

        if session_id and self.cookie_store:
            session = await self.cookie_store.get_session(session_id)
            if session:
                await self.cookie_store.renew_session(session_id, session, SESSION_TTL)
                # Cache session in RC for update_response to access permissions
                session['_session_id'] = session_id
                RequestContext.set_session(session)
                # Return through update_response (includes permissions from session)
                return await update_response({"refresh": "successful"})

        # No session - return error via Notification
        Notification.error(HTTP.UNAUTHORIZED, "No active session")
