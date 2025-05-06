from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Any
from app.models.url_model import Url, UrlCreate, UrlRead
from beanie import PydanticObjectId
import logging
import json

router = APIRouter()

# CREATE
@router.post('/')
async def create_url(item: UrlCreate):
    logging.info("Received request to create a new url.")
    # Instantiate a document from the model
    doc = Url(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"Url created successfully with _id: {doc._id}")
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception("Failed to create url.")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# GET ALL
@router.get('/')
async def get_all_urls():
    logging.info("Received request to fetch all urls.")
    try:
        docs = await Url.find_all()
        logging.info(f"Fetched {len(docs)} url(s) successfully.")
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception("Failed to fetch all urls.")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return docs

# GET ONE BY ID
@router.get('/{item_id}')
async def get_url(item_id: str):
    logging.info(f"Received request to fetch url with _id: {item_id}")
    try:
        doc = await Url.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Url with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='Url not found')
        logging.info(f"Fetched url with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to fetch Url with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# UPDATE
@router.put('/{item_id}')
async def update_url(item_id: str, item: UrlCreate):
    logging.info(f"Received request to update url with _id: {item_id}")
    try:
        doc = await Url.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Url with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='Url not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"Url with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to update Url with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# DELETE
@router.delete('/{item_id}')
async def delete_url(item_id: str):
    logging.info(f"Received request to delete url with _id: {item_id}")
    try:
        doc = await Url.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Url with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='Url not found')
        await doc.delete()
        logging.info(f"Url with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to delete Url with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return {'message': 'Url deleted successfully'}

# GET METADATA
@router.get('/metadata')
async def get_url_metadata():
    """Get metadata for Url entity."""
    return Url.get_metadata()