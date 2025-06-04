from fastapi import APIRouter
from typing import List, Dict, Any
from ..models.user_model import User, UserCreate, UserUpdate
from ..errors import ValidationError, NotFoundError, DuplicateError, DatabaseError
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("", response_model=List[User])
async def list_users() -> List[User]:
    """List all users"""
    users = await User.find_all()
    return list(users)  # Convert Sequence to List

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str) -> User:
    """Get a specific user by ID"""
    user = await User.get(user_id)
    if not user:
        raise NotFoundError("User", user_id)
    return user

@router.post("", response_model=User)
async def create_user(user_data: UserCreate) -> User:
    """Create a new user"""
    user = User(**user_data.model_dump())
    return await user.save()

@router.put("/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: UserUpdate) -> User:
    """Update an existing user"""
    # Check if user exists
    existing = await User.get(user_id)
    if not existing:
        raise NotFoundError("User", user_id)
    
    # Update fields
    user = User(**user_data.model_dump())
    user.id = user_id
    user.createdAt = existing.createdAt
    
    # Save changes
    return await user.save()

@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete a user"""
    user = await User.get(user_id)
    if not user:
        raise NotFoundError("User", user_id)
    await user.delete()
    return {"message": "User deleted successfully"}

@router.get("/metadata")
async def get_user_metadata():
    """Get metadata for User entity."""
    return User.get_metadata()