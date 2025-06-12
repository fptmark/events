from fastapi import APIRouter
from typing import List
import logging
from app.models.crawl_model import Crawl, CrawlCreate, CrawlUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[Crawl])
async def list_crawls() -> dict:
    """List all crawls"""
    try:
        logger.info("Fetching all crawls")
        crawls, validation_errors = await Crawl.find_all()
        records = len(crawls)
        logger.info(f"Retrieved {records} crawls")
        return list(crawls)

        response = {
            "data": list(crawl),
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
        logger.error(f"Error listing crawls: {e}")
        raise


@router.get("/{crawl_id}", response_model=Crawl)
async def get_crawl(crawl_id: str) -> Crawl:
    """Get a specific crawl by ID"""
    try:
        logger.info(f"Fetching crawl with ID: {crawl_id }")
        crawl = await Crawl.get(crawl_id)
        logger.info(f"Retrieved crawl: {crawl.id }")
        return crawl
    except NotFoundError:
        logger.warning(f"Crawl not found: {crawl_id }")
        raise
    except Exception as e:
        logger.error(f"Error getting crawl {crawl_id }: {e}")
        raise


@router.post("", response_model=Crawl)
async def create_crawl(crawl_data: CrawlCreate) -> Crawl:
    """Create a new crawl"""
    try:
        logger.info(f"Creating crawl with data: {crawl_data }")
        crawl = Crawl(**crawl_data.model_dump())
        result = await crawl.save()
        logger.info(f"Crawl created successfully with ID: {result.id}")
        return result
    except (ValidationError, DuplicateError) as e:
        logger.warning(f"Validation error creating crawl: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating crawl: {e}")
        raise


@router.put("/{crawl_id}", response_model=Crawl)
async def update_crawl(crawl_id: str, crawl_data: CrawlUpdate) -> Crawl:
    """Update an existing crawl"""
    try:
        logger.info(f"Updating crawl {crawl_id } with data: {crawl_data }")

        existing = await Crawl.get(crawl_id)
        logger.info(f"Found existing crawl: {existing.id}")

        crawl = Crawl(**crawl_data.model_dump())
        result = await crawl.save(crawl_id)
        logger.info(f"Crawl updated successfully: {result.id}")
        return result
    except (NotFoundError, ValidationError, DuplicateError) as e:
        logger.warning(f"Error updating crawl {crawl_id}: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating crawl {crawl_id}: {e}")
        raise


@router.delete("/{crawl_id}")
async def delete_crawl(crawl_id: str):
    """Delete a crawl"""
    try:
        logger.info(f"Deleting crawl: {crawl_id}")
        crawl = await Crawl.get(crawl_id)
        await crawl.delete()
        logger.info(f"Crawl deleted successfully: {crawl_id}")
        return {"message": "Crawl deleted successfully"}
    except NotFoundError:
        logger.warning(f"Crawl not found for deletion: {crawl_id}")
        raise