from fastapi import APIRouter
from typing import List
import logging
from app.models.url_model import Url, UrlCreate, UrlUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[Url])
async def list_urls() -> dict:
    """List all urls"""
    try:
        logger.info("Fetching all urls")
        urls, validation_errors = await Url.find_all()
        records = len(urls)
        logger.info(f"Retrieved {records} urls")
        return list(urls)

        response = {
            "data": list(url),
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
        logger.error(f"Error listing urls: {e}")
        raise


@router.get("/{url_id}", response_model=Url)
async def get_url(url_id: str) -> Url:
    """Get a specific url by ID"""
    try:
        logger.info(f"Fetching url with ID: {url_id }")
        url = await Url.get(url_id)
        logger.info(f"Retrieved url: {url.id }")
        return url
    except NotFoundError:
        logger.warning(f"Url not found: {url_id }")
        raise
    except Exception as e:
        logger.error(f"Error getting url {url_id }: {e}")
        raise


@router.post("", response_model=Url)
async def create_url(url_data: UrlCreate) -> Url:
    """Create a new url"""
    try:
        logger.info(f"Creating url with data: {url_data }")
        url = Url(**url_data.model_dump())
        result = await url.save()
        logger.info(f"Url created successfully with ID: {result.id}")
        return result
    except (ValidationError, DuplicateError) as e:
        logger.warning(f"Validation error creating url: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating url: {e}")
        raise


@router.put("/{url_id}", response_model=Url)
async def update_url(url_id: str, url_data: UrlUpdate) -> Url:
    """Update an existing url"""
    try:
        logger.info(f"Updating url {url_id } with data: {url_data }")

        existing = await Url.get(url_id)
        logger.info(f"Found existing url: {existing.id}")

        url = Url(**url_data.model_dump())
        result = await url.save(url_id)
        logger.info(f"Url updated successfully: {result.id}")
        return result
    except (NotFoundError, ValidationError, DuplicateError) as e:
        logger.warning(f"Error updating url {url_id}: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating url {url_id}: {e}")
        raise


@router.delete("/{url_id}")
async def delete_url(url_id: str):
    """Delete a url"""
    try:
        logger.info(f"Deleting url: {url_id}")
        url = await Url.get(url_id)
        await url.delete()
        logger.info(f"Url deleted successfully: {url_id}")
        return {"message": "Url deleted successfully"}
    except NotFoundError:
        logger.warning(f"Url not found for deletion: {url_id}")
        raise