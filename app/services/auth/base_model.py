from pydantic import BaseModel
from typing import Optional

def expose_response(endpoint: str):
    def decorator(cls):
        cls._expose_response = {"endpoint": endpoint}
        return cls
    return decorator

class AuthResponse(BaseModel):
    success: bool
    message: str

@expose_response("/login")
class LoginResponse(AuthResponse):
    session_id: Optional[str] = None

@expose_response("/logout")
class LogoutResponse(AuthResponse):
    success: bool

@expose_response("/refresh")
class RefreshResponse(AuthResponse):
    new_expiration: Optional[int] = None  # e.g., new TTL in seconds
