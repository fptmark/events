from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Any
from app.models.tagaffinity_model import TagAffinity, TagAffinityCreate, TagAffinityRead
from beanie import PydanticObjectId
import logging
import json

router = APIRouter()

# CREATE
@router.post('/')
async def create_tagaffinity(item: TagAffinityCreate):
    logging.info("Received request to create a new tagaffinity.")
    # Instantiate a document from the model
    doc = TagAffinity(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"TagAffinity created successfully with _id: {doc._id}")
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception("Failed to create tagaffinity.")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# GET ALL
@router.get('/')
async def get_all_tagaffinitys():
    logging.info("Received request to fetch all tagaffinitys.")
    try:
        docs = await TagAffinity.find_all().to_list()
        logging.info(f"Fetched {len(docs)} tagaffinity(s) successfully.")
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception("Failed to fetch all tagaffinitys.")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return docs

# GET ONE BY ID
@router.get('/{item_id}')
async def get_tagaffinity(item_id: str):
    logging.info(f"Received request to fetch tagaffinity with _id: {item_id}")
    try:
        doc = await TagAffinity.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"TagAffinity with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='TagAffinity not found')
        logging.info(f"Fetched tagaffinity with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to fetch TagAffinity with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# UPDATE
@router.put('/{item_id}')
async def update_tagaffinity(item_id: str, item: TagAffinityCreate):
    logging.info(f"Received request to update tagaffinity with _id: {item_id}")
    try:
        doc = await TagAffinity.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"TagAffinity with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='TagAffinity not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"TagAffinity with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to update TagAffinity with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# DELETE
@router.delete('/{item_id}')
async def delete_tagaffinity(item_id: str):
    logging.info(f"Received request to delete tagaffinity with _id: {item_id}")
    try:
        doc = await TagAffinity.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"TagAffinity with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='TagAffinity not found')
        await doc.delete()
        logging.info(f"TagAffinity with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to delete TagAffinity with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return {'message': 'TagAffinity deleted successfully'}

# GET METADATA
@router.get('/metadata')
async def get_tagaffinity_metadata():
    """Get metadata for TagAffinity entity."""
    return TagAffinity.get_metadata()