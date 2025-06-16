from fastapi import APIRouter
from typing import List
import logging
from app.models.userevent_model import UserEvent, UserEventCreate, UserEventUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[UserEvent])
async def list_userevents() -> List[UserEvent]:
    """List all userevents"""
    try:
        logger.info("Fetching all userevents")
        userevents, validation_errors = await UserEvent.find_all()
        records = len(userevents)
        logger.info(f"Retrieved {records} userevents")
        return list(userevents)
    except Exception as e:
        logger.error(f"Error listing userevents: {e}")
        raise


@router.get("/{userevent_id}", response_model=UserEvent)
async def get_userevent(userevent_id: str) -> UserEvent:
    """Get a specific userevent by ID"""
    try:
        logger.info(f"Fetching userevent with ID: {userevent_id }")
        userevent = await UserEvent.get(userevent_id)
        logger.info(f"Retrieved userevent: {userevent.id }")
        return userevent
    except NotFoundError:
        logger.warning(f"UserEvent not found: {userevent_id }")
        raise
    except Exception as e:
        logger.error(f"Error getting userevent {userevent_id }: {e}")
        raise


@router.post("", response_model=UserEvent)
async def create_userevent(userevent_data: UserEventCreate) -> UserEvent:
    """Create a new userevent"""
    try:
        logger.info(f"Creating userevent with data: {userevent_data }")
        userevent = UserEvent(**userevent_data.model_dump())
        result = await userevent.save()
        logger.info(f"UserEvent created successfully with ID: {result.id}")
        return result
    except (ValidationError, DuplicateError) as e:
        logger.warning(f"Validation error creating userevent: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating userevent: {e}")
        raise


@router.put("/{userevent_id}", response_model=UserEvent)
async def update_userevent(userevent_id: str, userevent_data: UserEventUpdate) -> UserEvent:
    """Update an existing userevent"""
    try:
        logger.info(f"Updating userevent {userevent_id } with data: {userevent_data }")

        existing = await UserEvent.get(userevent_id)
        logger.info(f"Found existing userevent: {existing.id}")

        userevent = UserEvent(**userevent_data.model_dump())
        result = await userevent.save(userevent_id)
        logger.info(f"UserEvent updated successfully: {result.id}")
        return result
    except (NotFoundError, ValidationError, DuplicateError) as e:
        logger.warning(f"Error updating userevent {userevent_id}: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating userevent {userevent_id}: {e}")
        raise


@router.delete("/{userevent_id}")
async def delete_userevent(userevent_id: str):
    """Delete a userevent"""
    try:
        logger.info(f"Deleting userevent: {userevent_id}")
        userevent = await UserEvent.get(userevent_id)
        await userevent.delete()
        logger.info(f"UserEvent deleted successfully: {userevent_id}")
        return {"message": "UserEvent deleted successfully"}
    except NotFoundError:
        logger.warning(f"UserEvent not found for deletion: {userevent_id}")
        raise