from fastapi import APIRouter
from typing import List
import logging
from app.models.tagaffinity_model import TagAffinity, TagAffinityCreate, TagAffinityUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[TagAffinity])
async def list_tagaffinitys() -> dict:
    """List all tagaffinitys"""
    try:
        logger.info("Fetching all tagaffinitys")
        tagaffinitys, validation_errors = await TagAffinity.find_all()
        records = len(tagaffinitys)
        logger.info(f"Retrieved {records} tagaffinitys")
        return list(tagaffinitys)

        response = {
            "data": list(tagaffinity),
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
        logger.error(f"Error listing tagaffinitys: {e}")
        raise


@router.get("/{tagaffinity_id}", response_model=TagAffinity)
async def get_tagaffinity(tagaffinity_id: str) -> TagAffinity:
    """Get a specific tagaffinity by ID"""
    try:
        logger.info(f"Fetching tagaffinity with ID: {tagaffinity_id }")
        tagaffinity = await TagAffinity.get(tagaffinity_id)
        logger.info(f"Retrieved tagaffinity: {tagaffinity.id }")
        return tagaffinity
    except NotFoundError:
        logger.warning(f"TagAffinity not found: {tagaffinity_id }")
        raise
    except Exception as e:
        logger.error(f"Error getting tagaffinity {tagaffinity_id }: {e}")
        raise


@router.post("", response_model=TagAffinity)
async def create_tagaffinity(tagaffinity_data: TagAffinityCreate) -> TagAffinity:
    """Create a new tagaffinity"""
    try:
        logger.info(f"Creating tagaffinity with data: {tagaffinity_data }")
        tagaffinity = TagAffinity(**tagaffinity_data.model_dump())
        result = await tagaffinity.save()
        logger.info(f"TagAffinity created successfully with ID: {result.id}")
        return result
    except (ValidationError, DuplicateError) as e:
        logger.warning(f"Validation error creating tagaffinity: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating tagaffinity: {e}")
        raise


@router.put("/{tagaffinity_id}", response_model=TagAffinity)
async def update_tagaffinity(tagaffinity_id: str, tagaffinity_data: TagAffinityUpdate) -> TagAffinity:
    """Update an existing tagaffinity"""
    try:
        logger.info(f"Updating tagaffinity {tagaffinity_id } with data: {tagaffinity_data }")

        existing = await TagAffinity.get(tagaffinity_id)
        logger.info(f"Found existing tagaffinity: {existing.id}")

        tagaffinity = TagAffinity(**tagaffinity_data.model_dump())
        result = await tagaffinity.save(tagaffinity_id)
        logger.info(f"TagAffinity updated successfully: {result.id}")
        return result
    except (NotFoundError, ValidationError, DuplicateError) as e:
        logger.warning(f"Error updating tagaffinity {tagaffinity_id}: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating tagaffinity {tagaffinity_id}: {e}")
        raise


@router.delete("/{tagaffinity_id}")
async def delete_tagaffinity(tagaffinity_id: str):
    """Delete a tagaffinity"""
    try:
        logger.info(f"Deleting tagaffinity: {tagaffinity_id}")
        tagaffinity = await TagAffinity.get(tagaffinity_id)
        await tagaffinity.delete()
        logger.info(f"TagAffinity deleted successfully: {tagaffinity_id}")
        return {"message": "TagAffinity deleted successfully"}
    except NotFoundError:
        logger.warning(f"TagAffinity not found for deletion: {tagaffinity_id}")
        raise