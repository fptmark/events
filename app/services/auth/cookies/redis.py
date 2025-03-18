# app/services/auth/cookies/redis.py
from typing import Optional
import uuid
import json
import time
import redis.asyncio as redis
from fastapi import Request
from ..base_router import BaseAuth, BaseCookieStore

# Configuration constants – these could be loaded from config.json later.
SESSION_TTL = 3600              # 1 hour in seconds
NEAR_EXPIRY_THRESHOLD = 300     # 5 minutes threshold

# --- Concrete Cookie Store Implementation Using Async Redis ---
class RedisCookieStore(BaseCookieStore):
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
class CookiesAuth(BaseAuth):
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

    async def login(self, credentials: dict) -> bool:
        # Placeholder: replace with proper credential validation in production.
        if credentials.get("username") == "user" and credentials.get("password") == "pass" and self.cookie_store:
            session_id = str(uuid.uuid4())
            session_data = {
                "user_id": credentials.get("username"),
                "created": time.time()
            }
            await self.cookie_store.set_session(session_id, session_data, SESSION_TTL)
            return True
        return False

    async def logout(self, request: Request) -> bool:
        token = request.cookies.get(self.cookie_name)
        if token and self.cookie_store:
            await self.cookie_store.delete_session(token)
            return True
        return False

    async def refresh(self, request: Request) -> bool:
        token = request.cookies.get(self.cookie_name)
        if token and self.cookie_store:
            session = await self.cookie_store.get_session(token)
            if session:
                await self.cookie_store.renew_session(token, session, SESSION_TTL)
                return True
        return False
