from fastapi import APIRouter
from typing import List
from ..models.tagaffinity_model import TagAffinity
from ..errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

router = APIRouter()

@router.get("/", response_model=List[TagAffinity])
async def list_tagaffinities() -> List[TagAffinity]:
    """List all tag affinities"""
    tagaffinities = await TagAffinity.find_all()
    return list(tagaffinities)  # Convert Sequence to List

@router.get("/{tagaffinity_id}", response_model=TagAffinity)
async def get_tagaffinity(tagaffinity_id: str) -> TagAffinity:
    """Get a specific tag affinity by ID"""
    return await TagAffinity.get(tagaffinity_id)

@router.post("/", response_model=TagAffinity)
async def create_tagaffinity(tagaffinity: TagAffinity) -> TagAffinity:
    """Create a new tag affinity"""
    # Validation is handled by Pydantic model
    return await tagaffinity.save()

@router.put("/{tagaffinity_id}", response_model=TagAffinity)
async def update_tagaffinity(tagaffinity_id: str, tagaffinity: TagAffinity) -> TagAffinity:
    """Update an existing tag affinity"""
    # Check if tag affinity exists
    existing = await TagAffinity.get(tagaffinity_id)
    
    # Update fields
    tagaffinity.id = tagaffinity_id
    tagaffinity.createdAt = existing.createdAt
    
    # Save changes
    return await tagaffinity.save()

@router.delete("/{tagaffinity_id}")
async def delete_tagaffinity(tagaffinity_id: str):
    """Delete a tag affinity"""
    tagaffinity = await TagAffinity.get(tagaffinity_id)
    await tagaffinity.delete()
    return {"message": "Tag affinity deleted successfully"}

@router.get('/metadata')
async def get_tagaffinity_metadata():
    """Get metadata for TagAffinity entity."""
    return TagAffinity.get_metadata() 