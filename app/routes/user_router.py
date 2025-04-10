from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Any
from app.models.user_model import User, UserCreate, UserRead
from beanie import PydanticObjectId
import logging
import json

router = APIRouter()

# CREATE
@router.post('/')
async def create_user(item: UserCreate):
    logging.info("Received request to create a new user.")
    # Instantiate a document from the model
    doc = User(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"User created successfully with _id: {doc._id}")
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception("Failed to create user.")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# GET ALL
@router.get('/')
async def get_all_users():
    logging.info("Received request to fetch all users.")
    try:
        docs = await User.find_all().to_list()
        logging.info(f"Fetched {len(docs)} user(s) successfully.")
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception("Failed to fetch all users.")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return docs

# GET ONE BY ID
@router.get('/{item_id}')
async def get_user(item_id: str):
    logging.info(f"Received request to fetch user with _id: {item_id}")
    try:
        doc = await User.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"User with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='User not found')
        logging.info(f"Fetched user with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to fetch User with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# UPDATE
@router.put('/{item_id}')
async def update_user(item_id: str, item: UserCreate):
    logging.info(f"Received request to update user with _id: {item_id}")
    try:
        doc = await User.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"User with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='User not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"User with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to update User with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return doc

# DELETE
@router.delete('/{item_id}')
async def delete_user(item_id: str):
    logging.info(f"Received request to delete user with _id: {item_id}")
    try:
        doc = await User.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"User with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='User not found')
        await doc.delete()
        logging.info(f"User with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        msg = str(e).replace('\n', ' ')
        logging.exception(f"Failed to delete User with _id: {item_id}")
        raise HTTPException(status_code=500, detail=f'Internal Server Error: {msg}')
    
    return {'message': 'User deleted successfully'}

# GET METADATA
@router.get('/metadata')
async def get_user_metadata():
    """Get metadata for User entity."""
    return User.get_metadata()