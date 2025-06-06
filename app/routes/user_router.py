from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any
from app.models.user_model import User, UserCreate, UserUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=List[User])
async def list_users() -> List[User]:
    """List all users"""
    try:
        users = await User.find_all()
        return list(users)  # Convert Sequence to List
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str) -> User:
    """Get a specific user by ID"""
    try:
        user = await User.get(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise

@router.post("", response_model=User)
async def create_user(user_data: UserCreate) -> User:
    """Create a new user"""
    try:
        logger.info(f"Creating user with data: {user_data}")
        user = User(**user_data.model_dump())
        result = await user.save()
        logger.info(f"User created successfully")
        return result
    except (ValidationError, DuplicateError) as e:
        # Log the error and re-raise - these will be handled by the global error handlers
        logger.error(f"Validation error creating user: {type(e).__name__}: {str(e)}")
        if hasattr(e, 'to_dict'):
            logger.error(f"Error details: {e.to_dict()}")
        raise
    except DatabaseError as e:
        # Log database errors and re-raise
        logger.error(f"Database error creating user: {str(e)}")
        raise
    except Exception as e:
        # Log unexpected errors and wrap them
        logger.error(f"Unexpected error creating user: {e}", exc_info=True)
        raise DatabaseError(str(e), "User", "create")

@router.put("/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: UserUpdate) -> User:
    """Update an existing user"""
    try:
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
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise

@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete a user"""
    try:
        user = await User.get(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        await user.delete()
        return {"message": "User deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise

@router.get("/metadata")
async def get_user_metadata():
    """Get metadata for User entity."""
    return User.get_metadata()