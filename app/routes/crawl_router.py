from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Any
from app.models.crawl_model import Crawl, CrawlCreate, CrawlRead
from beanie import PydanticObjectId
import logging
import json

router = APIRouter()

# Helper function to wrap response with metadata
def wrap_response(data, include_metadata=True):
    """Wrap response data with metadata for UI generation."""
    if not include_metadata:
        return data
    
    return {
        "data": data,
        "metadata": Crawl.get_metadata()
    }
    
# Helper function to wrap collection response with metadata
def wrap_collection_response(data_list, include_metadata=True):
    """Wrap response data list with metadata for UI generation."""
    if not include_metadata:
        return data_list
    
    return {
        "data": data_list,
        "metadata": Crawl.get_metadata()
    }
    
# CREATE
@router.post('/')
async def create_crawl(item: CrawlCreate, include_metadata: bool = True):
    logging.info("Received request to create a new crawl.")
    # Instantiate a document from the model
    doc = Crawl(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"Crawl created successfully with _id: {doc._id}")
    except Exception as e:
        logging.exception("Failed to create crawl.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# GET ALL
@router.get('/')
async def get_all_crawls(include_metadata: bool = True):
    logging.info("Received request to fetch all crawls.")
    try:
        docs = await Crawl.find_all().to_list()
        logging.info(f"Fetched {len(docs)} crawl(s) successfully.")
    except Exception as e:
        logging.exception("Failed to fetch all crawls.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_collection_response(docs, include_metadata)

# GET ONE BY ID
@router.get('/{item_id}')
async def get_crawl(item_id: str, include_metadata: bool = True):
    logging.info(f"Received request to fetch crawl with _id: {item_id}")
    try:
        doc = await Crawl.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Crawl with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='Crawl not found')
        logging.info(f"Fetched crawl with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to fetch Crawl with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# UPDATE
@router.put('/{item_id}')
async def update_crawl(item_id: str, item: CrawlCreate, include_metadata: bool = True):
    logging.info(f"Received request to update crawl with _id: {item_id}")
    try:
        doc = await Crawl.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Crawl with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='Crawl not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"Crawl with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to update Crawl with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# DELETE
@router.delete('/{item_id}')
async def delete_crawl(item_id: str):
    logging.info(f"Received request to delete crawl with _id: {item_id}")
    try:
        doc = await Crawl.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Crawl with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='Crawl not found')
        await doc.delete()
        logging.info(f"Crawl with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to delete Crawl with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return {'message': 'Crawl deleted successfully'}

# GET METADATA
@router.get('/metadata')
async def get_crawl_metadata():
    """Get metadata for Crawl entity."""
    return Crawl.get_metadata()