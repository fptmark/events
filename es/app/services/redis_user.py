from fastapi import APIRouter, Request, Response, HTTPException, Query
from typing import Dict, Any

# Dynamically import the concrete service implementation.
from app.services.redis_provider import CookiesAuth

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
async def login_endpoint(request: Request, response: Response, include_metadata: bool = True):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
    try:
        result = await CookiesAuth().login(payload)
        return wrap_response(result, include_metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout", summary="Logout")
async def logout_endpoint(request: Request, response: Response, include_metadata: bool = True):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
    try:
        result = await CookiesAuth().logout(payload)
        return wrap_response(result, include_metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh", summary="Refresh")
async def refresh_endpoint(request: Request, response: Response, include_metadata: bool = True):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
    try:
        result = await CookiesAuth().refresh(payload)
        return wrap_response(result, include_metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET METADATA
@router.get('/metadata', summary="Get metadata")
async def get_user_metadata():
    """Get metadata for User entity."""
    return User.get_metadata()

def init_router(app):
    app.include_router(router, prefix="/user/auth", tags=["User"])