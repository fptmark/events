from fastapi import APIRouter
from typing import List
from app.models.url_model import Url
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

router = APIRouter()

@router.get("/", response_model=List[Url])
async def list_urls() -> List[Url]:
    """List all URLs"""
    urls = await Url.find_all()
    return list(urls)  # Convert Sequence to List

@router.get("/{url_id}", response_model=Url)
async def get_url(url_id: str) -> Url:
    """Get a specific URL by ID"""
    return await Url.get(url_id)

@router.post("/", response_model=Url)
async def create_url(url: Url) -> Url:
    """Create a new URL"""
    # Validation is handled by Pydantic model
    return await url.save()

@router.put("/{url_id}", response_model=Url)
async def update_url(url_id: str, url: Url) -> Url:
    """Update an existing URL"""
    # Check if URL exists
    existing = await Url.get(url_id)
    
    # Update fields
    url.id = url_id
    url.createdAt = existing.createdAt
    
    # Save changes
    return await url.save()

@router.delete("/{url_id}")
async def delete_url(url_id: str):
    """Delete a URL"""
    url = await Url.get(url_id)
    if not url:
        raise NotFoundError("Url", url_id)
    await url.delete()
    return {"message": "URL deleted successfully"}

@router.get('/metadata')
async def get_url_metadata():
    """Get metadata for URL entity."""
    return Url.get_metadata()