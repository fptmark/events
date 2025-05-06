from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Any
from app.models.profile_model import Profile, ProfileCreate, ProfileRead
from beanie import PydanticObjectId
import logging
import json

router = APIRouter()

# CREATE
@router.post('/')
async def create_profile(item: ProfileCreate):
    logging.info("Received request to create a new profile.")
    # Instantiate a document from the model
    doc = Profile(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"Profile created successfully with _id: {doc._id}")
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception("Failed to create profile.")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# GET ALL
@router.get('/')
async def get_all_profiles():
    logging.info("Received request to fetch all profiles.")
    try:
        docs = await Profile.find_all()
        logging.info(f"Fetched {len(docs)} profile(s) successfully.")
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception("Failed to fetch all profiles.")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return docs

# GET ONE BY ID
@router.get('/{item_id}')
async def get_profile(item_id: str):
    logging.info(f"Received request to fetch profile with _id: {item_id}")
    try:
        doc = await Profile.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Profile with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='Profile not found')
        logging.info(f"Fetched profile with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to fetch Profile with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# UPDATE
@router.put('/{item_id}')
async def update_profile(item_id: str, item: ProfileCreate):
    logging.info(f"Received request to update profile with _id: {item_id}")
    try:
        doc = await Profile.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Profile with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='Profile not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"Profile with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to update Profile with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# DELETE
@router.delete('/{item_id}')
async def delete_profile(item_id: str):
    logging.info(f"Received request to delete profile with _id: {item_id}")
    try:
        doc = await Profile.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Profile with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='Profile not found')
        await doc.delete()
        logging.info(f"Profile with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to delete Profile with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return {'message': 'Profile deleted successfully'}

# GET METADATA
@router.get('/metadata')
async def get_profile_metadata():
    """Get metadata for Profile entity."""
    return Profile.get_metadata()