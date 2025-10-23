# app/services/auth/cookies/redis.py
from typing import Optional
import uuid
import json
import time
import redis.asyncio as redis
from fastapi import Request
from pydantic import BaseModel
from app.providers.framework.decorators import expose_endpoint

# Request/Response models
class LoginRequest(BaseModel):
    """Login credentials"""
    username: str
    password: str

class AuthResponse(BaseModel):
    """Standard auth response"""
    success: bool
    message: str | None = None

# Configuration constants – these could be loaded from config.json later.
SESSION_TTL = 3600              # 1 hour in seconds
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

    async def renew_session(self, session_id: str, session_data: dict, ttl: int) -> dict:
        if self.redis_client is None:
            raise RuntimeError("Redis client not connected")
        await self.redis_client.setex(session_id, ttl, json.dumps(session_data))
        return session_data

# --- Concrete CookiesAuth Implementation Using Async Redis ---
class CookiesAuth:
    # Default cookie configuration; can be overridden via config.
    cookie_name = "sessionId"
    cookie_options = {
        "httponly": True,
        "secure": True,    # For local development, you might set this to False if not using HTTPS.
        "samesite": "lax"
    }
    # The backing store will be set via the asynchronous initialize() class method.
    cookie_store: Optional[RedisCookieStore] = None

    @classmethod
    async def initialize(cls, config: dict):
        """
        Initialize the auth service using settings from config.
        Expected config keys: host, port, db (for Redis), etc.
        """
        store = RedisCookieStore(
            host=config.get("host", "127.0.0.1"),
            port=config.get("port", 6379),
            db=config.get("db", 0)
        )
        await store.connect()
        cls.cookie_store = store
        return cls

    async def authenticate(self, request: Request) -> bool:
        token = request.cookies.get(self.cookie_name)
        if not token or self.cookie_store is None:
            return False
        session = await self.cookie_store.get_session(token)
        return bool(session)

    @expose_endpoint(method="POST", route="/login", summary="Login")
    async def login(self, entity_name: str, credentials: dict) -> str | None:
        """
        Authenticate user and create session.

        Args:
            entity_name: Entity to authenticate against (e.g., "User", "Customer")
            credentials: dict with login and password values

        Returns:
            session_id if successful, None if invalid credentials
        """
        # Get service configuration from entity metadata
        from app.services.metadata import MetadataService

        metadata = MetadataService.get(entity_name)
        if not metadata:
            return None

        services = metadata.get("services", {})
        auth_config = services.get("auth.cookies.redis", {})
        field_map = auth_config.get("fields", {})

        if not field_map:
            return None

        login_field = field_map.get("login")
        password_field = field_map.get("password")

        if not login_field or not password_field:
            return None

        login_value = credentials.get(login_field)
        password_value = credentials.get(password_field)

        if not login_value or not password_value or not self.cookie_store:
            return None

        # Query database for user with EXACT match
        from app.db.factory import DatabaseFactory
        db = DatabaseFactory.get_instance()

        try:
            user_docs, count = await db.documents.get_all(
                entity_name,
                filter={login_field: login_value},
                pageSize=1,
                filter_matching="exact"
            )
        except Exception as e:
            return None

        if count == 0:
            return None

        user = user_docs[0]

        # TODO: Use bcrypt password verification in production
        # For now, plaintext comparison
        if user.get(password_field) != password_value:
            return None

        # Create session
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": str(user.get("id")),
            "entity": entity_name,
            "login_value": login_value,
            "created": time.time()
        }

        await self.cookie_store.set_session(session_id, session_data, SESSION_TTL)

        return session_id

    @expose_endpoint(method="POST", route="/logout", summary="Logout")
    async def logout(self, request: Request) -> bool:
        token = request.cookies.get(self.cookie_name)
        if token and self.cookie_store:
            await self.cookie_store.delete_session(token)
            return True
        return False

    @expose_endpoint(method="POST", route="/refresh", summary="Refresh session")
    async def refresh(self, request: Request) -> bool:
        token = request.cookies.get(self.cookie_name)
        if token and self.cookie_store:
            session = await self.cookie_store.get_session(token)
            if session:
                await self.cookie_store.renew_session(token, session, SESSION_TTL)
                return True
        return False
