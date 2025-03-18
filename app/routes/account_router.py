from fastapi import APIRouter, HTTPException, Response
from typing import List, Dict, Any
from app.models.account_model import Account, AccountCreate, AccountRead
from beanie import PydanticObjectId
import logging
import json

router = APIRouter()

# Helper function to wrap response with metadata
def wrap_response(data, include_metadata=True):
    """Wrap response data with metadata for UI generation."""
    if not include_metadata:
        return data
    
    result = {
        "data": data,
    }
    
    # Add metadata if requested
    if include_metadata:
        result["metadata"] = Account.get_metadata()
    
    return result

# Helper function to wrap collection response with metadata
def wrap_collection_response(data_list, include_metadata=True):
    """Wrap response data list with metadata for UI generation."""
    if not include_metadata:
        return data_list
    
    result = {
        "data": data_list,
    }
    
    # Add metadata if requested
    if include_metadata:
        result["metadata"] = Account.get_metadata()
    
    return result

# CREATE
@router.post('/')
async def create_account(item: AccountCreate, include_metadata: bool = True):
    logging.info("Received request to create a new account.")
    # Instantiate a document from the model
    doc = Account(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"Account created successfully with _id: {doc._id}")
    except Exception as e:
        logging.exception("Failed to create account.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# GET ALL
@router.get('/')
async def get_all_accounts(include_metadata: bool = True):
    logging.info("Received request to fetch all accounts.")
    try:
        docs = await Account.find_all().to_list()
        logging.info(f"Fetched {len(docs)} account(s) successfully.")
    except Exception as e:
        logging.exception("Failed to fetch all accounts.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_collection_response(docs, include_metadata)

# GET ONE BY ID
@router.get('/{item_id}')
async def get_account(item_id: str, include_metadata: bool = True):
    logging.info(f"Received request to fetch account with _id: {item_id}")
    try:
        doc = await Account.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Account with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='Account not found')
        logging.info(f"Fetched account with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to fetch Account with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# UPDATE
@router.put('/{item_id}')
async def update_account(item_id: str, item: AccountCreate, include_metadata: bool = True):
    logging.info(f"Received request to update account with _id: {item_id}")
    try:
        doc = await Account.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Account with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='Account not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"Account with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to update Account with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return wrap_response(doc, include_metadata)

# DELETE
@router.delete('/{item_id}')
async def delete_account(item_id: str):
    logging.info(f"Received request to delete account with _id: {item_id}")
    try:
        doc = await Account.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Account with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='Account not found')
        await doc.delete()
        logging.info(f"Account with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to delete Account with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    
    return {'message': 'Account deleted successfully'}

# GET METADATA
@router.get('/metadata')
async def get_account_metadata():
    """Get metadata for Account entity."""
    return Account.get_metadata()