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
from app.core.notify import Notification, HTTP
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
    # Entity-specific configurations: {'Auth': {route, inputs, outputs, delegates}, 'User': {...}}
    entity_configs: Dict[str, dict] = {}

    @classmethod
    async def initialize(cls, entity_configs: dict, runtime_config: dict):
        """
        Initialize the authn service with multiple entity configurations.

        Args:
            entity_configs: Dict of entity configs, e.g.:
                {'Auth': {route: '/login', inputs: {...}, outputs: [...], delegates: [...]},
                 'User': {route: '/login/user', inputs: {...}, outputs: [...], delegates: [...]}}
            runtime_config: Runtime settings (Redis host, port, db, etc.)
        """
        # Initialize Redis store (shared across all entity configs)
        store = RedisCookieStore(
            host=runtime_config.get("host", "127.0.0.1"),
            port=runtime_config.get("port", 6379),
            db=runtime_config.get("db", 0)
        )
        await store.connect()
        cls.cookie_store = store
        cls.entity_configs = entity_configs

        print(f"  Authn service configured for entities: {list(entity_configs.keys())}")
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
        # Initialize notification system (same as CRUD endpoints)
        Notification.start()

        # Extract credentials from request body
        credentials = await request.json()

        # Determine which entity config to use by matching request path
        path = request.url.path
        entity = ''

        for ent, config in self.entity_configs.items():
            config_route = config.get('route', '')
            normalized_route = f"/api/{config_route.strip('/')}"
            if path == normalized_route:
                entity = ent
                break

        if not entity or entity not in self.entity_configs:
            print(f"ERROR: No entity config found for path: {path}")
            Notification.error(HTTP.UNAUTHORIZED, "Invalid credentials")

        # Get entity-specific config
        config = self.entity_configs[entity]

        # Build input query from entity-specific input mappings
        input_query = {}
        field_mappings = config.get('inputs', {})

        for semantic_field, entity_field in field_mappings.items():
            credential_value = credentials.get(semantic_field)

            if not credential_value:
                Notification.error(HTTP.UNAUTHORIZED, "Invalid credentials")

            input_query[entity_field] = credential_value

        if not self.cookie_store:
            Notification.error(HTTP.UNAUTHORIZED, "Invalid credentials")

        # Query database for user with EXACT match
        from app.db.factory import DatabaseFactory
        db = DatabaseFactory.get_instance()

        try:
            output_fields = ['id', *config.get('outputs', [])]
            doc = await db.documents.bypass(entity, input_query, output_fields)
        except Exception as e:
            print(f"Error during user lookup: {str(e)}")
            Notification.error(HTTP.UNAUTHORIZED, "Invalid credentials")

        if doc is None:
            Notification.error(HTTP.UNAUTHORIZED, "Invalid credentials")

        # Create session
        session_id = str(uuid.uuid4())
        current_time = time.time()
        session_data = {
            **doc,       # Include all returned fields from doc
            "login_value": list(input_query.values())[0],  # First credential value
            "created": current_time,
            "absolute_expiry": current_time + ABSOLUTE_SESSION_MAX,  # Force re-login after absolute max
            "_authn_entity": entity  # Store which entity was used for login
        }

        # Handle delegates (e.g., authz)
        permissions = None
        delegates = config.get('delegates', [])

        for delegate in delegates:
            # Delegate format: {"authz": "Role"} or {"authz": null}
            delegate_type = list(delegate.keys())[0]  # e.g., "authz"
            delegate_entity = delegate[delegate_type]  # e.g., "Role" or null

            if delegate_type == "authz":
                # Call authz delegate
                authz_service = ServiceManager.get_service_instance("authz")
                if authz_service:
                    roleId = session_data.get('roleId')
                    if roleId:
                        try:
                            # Get expanded permissions (cached in RBAC, returned to client at login)
                            # Pass delegate_entity so authz knows which entity to use
                            permissions = await authz_service.get_permissions(roleId, delegate_entity)
                            if permissions and permissions.get("entity"):
                                print(f"Login: Retrieved permissions for roleId {roleId} from {delegate_entity}: {permissions}")
                                # Store authz entity in session for future requests
                                session_data["_authz_entity"] = delegate_entity
                            else:
                                print(f"ERROR: get_permissions returned empty for roleId {roleId}: {permissions}")
                                Notification.error(HTTP.UNAUTHORIZED, "No permissions defined for role")
                        except Exception as e:
                            # Role not found or other error - FAIL login since authz is configured
                            print(f"ERROR: Could not fetch permissions for role {roleId}: {e}")
                            Notification.error(HTTP.UNAUTHORIZED, f"Failed to load permissions: {str(e)}")

        # NOTE: Permissions NOT stored in session - RBAC caches them by roleId
        # Session only stores roleId and entity context, gating will fetch permissions from RBAC cache

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
            "login": session_data.get("login_value"),
            "permissions": permissions  # Expanded permissions for UI (sent only at login)
        }
        return await update_response(login_data)

    @decorators.expose_endpoint(method="POST", route="/logout", summary="Logout")
    async def logout(self, request: Request, response: Response) -> Dict[str, any]:
        # Initialize notification system (same as CRUD endpoints)
        Notification.start()

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
        # Initialize notification system (same as CRUD endpoints)
        Notification.start()

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

    @decorators.expose_endpoint(method="GET", route="/session", summary="Get current session")
    async def get_session(self, request: Request, response: Response) -> Dict[str, any]:
        """
        Get current session data if valid session exists.
        Used by UI on page refresh to restore permissions without re-login.

        Returns:
            dict with login, roleId, and permissions if valid session exists
            401 error if no valid session
        """
        # Initialize notification system (same as CRUD endpoints)
        Notification.start()

        # Set up RequestContext with session from cookie
        from app.core.request_context import RequestContext
        from app.routers.endpoint_handlers import update_response

        session_id = request.cookies.get(self.cookie_name)
        RequestContext.set_session_id(session_id)

        if not session_id or not self.cookie_store:
            Notification.error(HTTP.UNAUTHORIZED, "No active session")

        session = await self.cookie_store.get_session(session_id)
        if not session:
            Notification.error(HTTP.UNAUTHORIZED, "No active session")

        # Check absolute expiry (same as authorized() method)
        absolute_expiry = session.get('absolute_expiry', 0)
        if time.time() > absolute_expiry:
            await self.cookie_store.delete_session(session_id)
            Notification.error(HTTP.UNAUTHORIZED, "Session expired")

        # Get expanded permissions from authz service if running (same as login)
        permissions = None
        authz_service = ServiceManager.get_service_instance("authz")
        if authz_service:
            roleId = session.get('roleId')
            authz_entity = session.get('_authz_entity')  # Get authz entity from session
            if roleId:
                try:
                    # Get expanded permissions (cached in RBAC)
                    permissions = await authz_service.get_permissions(roleId, entity=authz_entity)
                    if permissions and permissions.get("entity"):
                        print(f"Session: Retrieved permissions for roleId {roleId} from {authz_entity}: {permissions}")
                    else:
                        print(f"ERROR: get_permissions returned empty for roleId {roleId}: {permissions}")
                except Exception as e:
                    print(f"ERROR: Could not fetch permissions for role {roleId}: {e}")
                    # Don't fail session fetch - return session without permissions

        # Cache session in RequestContext for update_response
        session['_session_id'] = session_id
        RequestContext.set_session(session)

        # Return session data through update_response (same pattern as login)
        session_data = {
            "sessionId": session_id,
            "login": session.get("login_value"),
            "roleId": session.get("roleId"),
            "permissions": permissions  # Expanded permissions for UI
        }
        return await update_response(session_data)
