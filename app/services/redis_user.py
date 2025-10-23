from fastapi import APIRouter, Request, Response, HTTPException, Query
from typing import Dict, Any

# Dynamically import the concrete service implementation.
from app.services.auth.cookies.redis_provider import CookiesAuth

# For metadata access
from app.models.user_model import User

router = APIRouter()

# Helper function to wrap response with metadata
def wrap_response(data, include_metadata=True):
    """Wrap response data with metadata for UI generation."""
    if not include_metadata:
        return data
    
    result = {
        "data": data,
    }
    
    # Add metadata if requested
    if include_metadata:
        result["metadata"] = User.get_metadata()
    
    return result

@router.post("/login", summary="Login")
async def login_endpoint(request: Request, response: Response):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    # Validate required fields
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username or password")

    # Authenticate and get session_id
    session_id = await CookiesAuth().login(payload)

    if session_id:
        # Set cookie
        response.set_cookie(
            key=CookiesAuth.cookie_name,
            value=session_id,
            **CookiesAuth.cookie_options
        )
        return {"success": True, "message": "Login successful"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/logout", summary="Logout")
async def logout_endpoint(request: Request, response: Response):
    # Pass Request object to logout
    success = await CookiesAuth().logout(request)

    if success:
        response.delete_cookie(key=CookiesAuth.cookie_name)
        return {"success": True, "message": "Logout successful"}
    else:
        raise HTTPException(status_code=400, detail="No active session")

@router.post("/refresh", summary="Refresh")
async def refresh_endpoint(request: Request, response: Response):
    # Pass Request object to refresh
    success = await CookiesAuth().refresh(request)

    if success:
        return {"success": True, "message": "Session refreshed"}
    else:
        raise HTTPException(status_code=401, detail="Session expired or invalid")


# GET METADATA
@router.get('/metadata', summary="Get metadata")
async def get_user_metadata():
    """Get metadata for User entity."""
    return User.get_metadata()

def init_router(app):
    app.include_router(router, prefix="/user/auth", tags=["User"])