from fastapi import APIRouter
from typing import List
from ..models.profile_model import Profile, ProfileCreate, ProfileUpdate
from ..errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

router = APIRouter()

@router.get("", response_model=List[Profile])
async def list_profiles() -> List[Profile]:
    """List all profiles"""
    profiles = await Profile.find_all()
    return list(profiles)  # Convert Sequence to List

@router.get("/{profile_id}", response_model=Profile)
async def get_profile(profile_id: str) -> Profile:
    """Get a specific profile by ID"""
    profile = await Profile.get(profile_id)
    if not profile:
        raise NotFoundError("Profile", profile_id)
    return profile

@router.post("", response_model=Profile)
async def create_profile(profile_data: ProfileCreate) -> Profile:
    """Create a new profile"""
    profile = Profile(**profile_data.model_dump())
    return await profile.save()

@router.put("/{profile_id}", response_model=Profile)
async def update_profile(profile_id: str, profile_data: ProfileUpdate) -> Profile:
    """Update an existing profile"""
    # Check if profile exists
    existing = await Profile.get(profile_id)
    if not existing:
        raise NotFoundError("Profile", profile_id)
    
    # Update fields
    profile = Profile(**profile_data.model_dump())
    profile.id = profile_id
    profile.createdAt = existing.createdAt
    
    # Save changes
    return await profile.save()

@router.delete("/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a profile"""
    profile = await Profile.get(profile_id)
    if not profile:
        raise NotFoundError("Profile", profile_id)
    await profile.delete()
    return {"message": "Profile deleted successfully"}

@router.get("/metadata")
async def get_profile_metadata():
    """Get metadata for Profile entity."""
    return Profile.get_metadata()