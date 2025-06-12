from fastapi import APIRouter
from typing import List
import logging
from app.models.profile_model import Profile, ProfileCreate, ProfileUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[Profile])
async def list_profiles() -> List[Profile]:
    """List all profiles"""
    try:
        logger.info("Fetching all profiles")
        profiles = await Profile.find_all()
        records = len(profiles)
        logger.info(f"Retrieved {records} profiles")
        return list(profiles)
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise


@router.get("/{profile_id}", response_model=Profile)
async def get_profile(profile_id: str) -> Profile:
    """Get a specific profile by ID"""
    try:
        logger.info(f"Fetching profile with ID: {profile_id }")
        profile = await Profile.get(profile_id)
        logger.info(f"Retrieved profile: {profile.id }")
        return profile
    except NotFoundError:
        logger.warning(f"Profile not found: {profile_id }")
        raise
    except Exception as e:
        logger.error(f"Error getting profile {profile_id }: {e}")
        raise


@router.post("", response_model=Profile)
async def create_profile(profile_data: ProfileCreate) -> Profile:
    """Create a new profile"""
    try:
        logger.info(f"Creating profile with data: {profile_data }")
        profile = Profile(**profile_data.model_dump())
        result = await profile.save()
        logger.info(f"Profile created successfully with ID: {result.id}")
        return result
    except (ValidationError, DuplicateError) as e:
        logger.warning(f"Validation error creating profile: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise


@router.put("/{profile_id}", response_model=Profile)
async def update_profile(profile_id: str, profile_data: ProfileUpdate) -> Profile:
    """Update an existing profile"""
    try:
        logger.info(f"Updating profile {profile_id } with data: {profile_data }")

        existing = await Profile.get(profile_id)
        logger.info(f"Found existing profile: {existing.id}")

        profile = Profile(**profile_data.model_dump())
        result = await profile.save(profile_id)
        logger.info(f"Profile updated successfully: {result.id}")
        return result
    except (NotFoundError, ValidationError, DuplicateError) as e:
        logger.warning(f"Error updating profile {profile_id}: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating profile {profile_id}: {e}")
        raise


@router.delete("/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a profile"""
    try:
        logger.info(f"Deleting profile: {profile_id}")
        profile = await Profile.get(profile_id)
        await profile.delete()
        logger.info(f"Profile deleted successfully: {profile_id}")
        return {"message": "Profile deleted successfully"}
    except NotFoundError:
        logger.warning(f"Profile not found for deletion: {profile_id}")
        raise