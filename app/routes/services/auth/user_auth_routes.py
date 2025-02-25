from fastapi import APIRouter, Request, Response, HTTPException

# Dynamically import the concrete service implementation.
from services.auth.cookies.redis import CookiesAuth as Auth

# Dynamically import all response models from the base_model.
from services.auth.base_model import *

router = APIRouter()

@router.post("/login", summary="", response_model=LoginResponse)
async def login_endpoint(request: Request, response: Response):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
    try:
        result = await Auth().login(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logout", summary="", response_model=LogoutResponse)
async def logout_endpoint(request: Request, response: Response):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
    try:
        result = await Auth().logout(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh", summary="", response_model=RefreshResponse)
async def refresh_endpoint(request: Request, response: Response):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")
    try:
        result = await Auth().refresh(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def init_router(app):
    app.include_router(router, prefix="/user/auth", tags=["User"])