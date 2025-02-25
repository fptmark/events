# app/services/auth/base.py
from abc import ABC, abstractmethod
from fastapi import Request

def expose_endpoint(method: str, route: str):
    def decorator(func):
        # Attach metadata to the function
        func._expose_endpoint = {"method": method, "route": route}
        return func
    return decorator

class BaseAuth(ABC):
    @abstractmethod
    async def authenticate(self, request: Request) -> bool:
        """
        Validate the incoming request. Return True if authenticated, False otherwise.
        """
        pass

    @expose_endpoint("POST", "/login")
    @abstractmethod
    async def login(self, credentials: dict) -> bool:
        """
        Validate credentials and create a session.
        Return True if login is successful.
        """
        pass

    @expose_endpoint("POST", "/logout")
    @abstractmethod
    async def logout(self, request: Request) -> None:
        """
        Log out the user by terminating their session.
        """
        pass

    @expose_endpoint("POST", "/refresh")
    @abstractmethod
    async def refresh(self, request: Request) -> bool:
        """
        Refresh the session if needed.
        Return True if the session was successfully refreshed.
        """
        pass

class BaseCookieStore(ABC):
    @abstractmethod
    async def set_session(self, session_id: str, session_data: dict, ttl: int) -> None:
        """
        Store session data with a time-to-live (TTL).
        """
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> dict:
        """
        Retrieve session data by session_id.
        """
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """
        Delete a session.
        """
        pass

    @abstractmethod
    async def renew_session(self, session_id: str, session_data: dict, ttl: int) -> dict:
        """
        Renew the session by resetting its TTL and return the updated session data.
        """
        pass
