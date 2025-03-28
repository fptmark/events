from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Any
from app.models.event_model import Event, EventCreate, EventRead
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
        "metadata": Event.get_metadata()
    }
    
# Helper function to wrap collection response with metadata
def wrap_collection_response(data_list, include_metadata=True):
    """Wrap response data list with metadata for UI generation."""
    if not include_metadata:
        return data_list
    
    return {
        "data": data_list,
        "metadata": Event.get_metadata()
    }
    
# CREATE
@router.post('/')
async def create_event(item: EventCreate, include_metadata: bool = True):
    logging.info("Received request to create a new event.")
    # Instantiate a document from the model
    doc = Event(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"Event created successfully with _id: {doc._id}")
    except Exception as e:
        logging.exception("Failed to create event.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# GET ALL
@router.get('/')
async def get_all_events(include_metadata: bool = True):
    logging.info("Received request to fetch all events.")
    try:
        docs = await Event.find_all().to_list()
        logging.info(f"Fetched {len(docs)} event(s) successfully.")
    except Exception as e:
        logging.exception("Failed to fetch all events.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_collection_response(docs, include_metadata)

# GET ONE BY ID
@router.get('/{item_id}')
async def get_event(item_id: str, include_metadata: bool = True):
    logging.info(f"Received request to fetch event with _id: {item_id}")
    try:
        doc = await Event.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Event with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='Event not found')
        logging.info(f"Fetched event with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to fetch Event with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# UPDATE
@router.put('/{item_id}')
async def update_event(item_id: str, item: EventCreate, include_metadata: bool = True):
    logging.info(f"Received request to update event with _id: {item_id}")
    try:
        doc = await Event.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Event with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='Event not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"Event with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to update Event with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# DELETE
@router.delete('/{item_id}')
async def delete_event(item_id: str):
    logging.info(f"Received request to delete event with _id: {item_id}")
    try:
        doc = await Event.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Event with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='Event not found')
        await doc.delete()
        logging.info(f"Event with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to delete Event with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return {'message': 'Event deleted successfully'}

# GET METADATA
@router.get('/metadata')
async def get_event_metadata():
    """Get metadata for Event entity."""
    return Event.get_metadata()