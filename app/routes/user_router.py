from fastapi import APIRouter
from typing import List
import logging
from app.models.user_model import User, UserCreate, UserUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[User])
async def list_users() -> dict:
    """List all users"""
    try:
        logger.info("Fetching all users")
        users, validation_errors = await User.find_all()
        records = len(users)
        logger.info(f"Retrieved {records} users")
        
        response = {
            "data": list(users),
            "validation_errors": [
                {
                    "message": ve.message,
                    "entity": ve.entity,
                    "invalid_fields": [f.to_dict() for f in ve.invalid_fields]
                }
                for ve in validation_errors
            ] if validation_errors else []
        }
        return response
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str) -> User:
    """Get a specific user by ID"""
    try:
        logger.info(f"Fetching user with ID: {user_id }")
        user = await User.get(user_id)
        logger.info(f"Retrieved user: {user.id }")
        return user
    except NotFoundError:
        logger.warning(f"User not found: {user_id }")
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id }: {e}")
        raise


@router.post("", response_model=User)
async def create_user(user_data: UserCreate) -> User:
    """Create a new user"""
    try:
        logger.info(f"Creating user with data: {user_data }")
        user = User(**user_data.model_dump())
        result = await user.save()
        logger.info(f"User created successfully with ID: {result.id}")
        return result
    except (ValidationError, DuplicateError) as e:
        logger.warning(f"Validation error creating user: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise


@router.put("/{user_id}", response_model=User)
async def update_user(user_id: str, user_data: UserUpdate) -> User:
    """Update an existing user"""
    try:
        logger.info(f"Updating user {user_id } with data: {user_data }")

        existing = await User.get(user_id)
        logger.info(f"Found existing user: {existing.id}")

        user = User(**user_data.model_dump())
        result = await user.save(user_id)
        logger.info(f"User updated successfully: {result.id}")
        return result
    except (NotFoundError, ValidationError, DuplicateError) as e:
        logger.warning(f"Error updating user {user_id}: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete a user"""
    try:
        logger.info(f"Deleting user: {user_id}")
        user = await User.get(user_id)
        await user.delete()
        logger.info(f"User deleted successfully: {user_id}")
        return {"message": "User deleted successfully"}
    except NotFoundError:
        logger.warning(f"User not found for deletion: {user_id}")
        raise