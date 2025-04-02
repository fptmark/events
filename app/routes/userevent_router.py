from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Any
from app.models.userevent_model import UserEvent, UserEventCreate, UserEventRead
from beanie import PydanticObjectId
import logging
import json

router = APIRouter()

# CREATE
@router.post('/')
async def create_userevent(item: UserEventCreate):
    logging.info("Received request to create a new userevent.")
    # Instantiate a document from the model
    doc = UserEvent(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"UserEvent created successfully with _id: {doc._id}")
    except Exception as e:
        logging.exception("Failed to create userevent.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return doc

# GET ALL
@router.get('/')
async def get_all_userevents():
    logging.info("Received request to fetch all userevents.")
    try:
        docs = await UserEvent.find_all().to_list()
        logging.info(f"Fetched {len(docs)} userevent(s) successfully.")
    except Exception as e:
        logging.exception("Failed to fetch all userevents.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return docs

# GET ONE BY ID
@router.get('/{item_id}')
async def get_userevent(item_id: str):
    logging.info(f"Received request to fetch userevent with _id: {item_id}")
    try:
        doc = await UserEvent.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"UserEvent with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='UserEvent not found')
        logging.info(f"Fetched userevent with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to fetch UserEvent with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return doc

# UPDATE
@router.put('/{item_id}')
async def update_userevent(item_id: str, item: UserEventCreate):
    logging.info(f"Received request to update userevent with _id: {item_id}")
    try:
        doc = await UserEvent.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"UserEvent with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='UserEvent not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"UserEvent with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to update UserEvent with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return doc

# DELETE
@router.delete('/{item_id}')
async def delete_userevent(item_id: str):
    logging.info(f"Received request to delete userevent with _id: {item_id}")
    try:
        doc = await UserEvent.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"UserEvent with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='UserEvent not found')
        await doc.delete()
        logging.info(f"UserEvent with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to delete UserEvent with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return {'message': 'UserEvent deleted successfully'}

# GET METADATA
@router.get('/metadata')
async def get_userevent_metadata():
    """Get metadata for UserEvent entity."""
    return UserEvent.get_metadata()