from fastapi import APIRouter
from typing import List
from ..models.crawl_model import Crawl, CrawlCreate, CrawlUpdate
from ..errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

router = APIRouter()

@router.get("/", response_model=List[Crawl])
async def list_crawls() -> List[Crawl]:
    """List all crawls"""
    crawls = await Crawl.find_all()
    return list(crawls)  # Convert Sequence to List

@router.get("/{crawl_id}", response_model=Crawl)
async def get_crawl(crawl_id: str) -> Crawl:
    """Get a specific crawl by ID"""
    crawl = await Crawl.get(crawl_id)
    if not crawl:
        raise NotFoundError("Crawl", crawl_id)
    return crawl

@router.post("/", response_model=Crawl)
async def create_crawl(crawl_data: CrawlCreate) -> Crawl:
    """Create a new crawl"""
    crawl = Crawl(**crawl_data.model_dump())
    return await crawl.save()

@router.put("/{crawl_id}", response_model=Crawl)
async def update_crawl(crawl_id: str, crawl_data: CrawlUpdate) -> Crawl:
    """Update an existing crawl"""
    # Check if crawl exists
    existing = await Crawl.get(crawl_id)
    if not existing:
        raise NotFoundError("Crawl", crawl_id)
    
    # Update fields
    crawl = Crawl(**crawl_data.model_dump())
    crawl.id = crawl_id
    crawl.createdAt = existing.createdAt
    
    # Save changes
    return await crawl.save()

@router.delete("/{crawl_id}")
async def delete_crawl(crawl_id: str):
    """Delete a crawl"""
    crawl = await Crawl.get(crawl_id)
    if not crawl:
        raise NotFoundError("Crawl", crawl_id)
    await crawl.delete()
    return {"message": "Crawl deleted successfully"}

@router.get('/metadata')
async def get_crawl_metadata():
    """Get metadata for Crawl entity."""
    return Crawl.get_metadata()