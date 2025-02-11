from fastapi import APIRouter, HTTPException
from typing import List
from app.models.userevent_model import Userevent, UsereventCreate, UsereventRead
from beanie import PydanticObjectId
import logging

router = APIRouter()

# CREATE
@router.post('/', response_model=UsereventRead)
async def create_userevent(item: UsereventCreate):
    logging.info("Received request to create a new userevent.")
    # Instantiate a document from the model
    doc = Userevent(**item.dict(exclude_unset=True))
    try:
        await doc.save()  # This triggers BaseEntity's default factories and save() override.
        logging.info(f"Userevent created successfully with _id: {doc._id}")
    except Exception as e:
        logging.exception("Failed to create userevent.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    return doc

# GET ALL
@router.get('/', response_model=List[UsereventRead])
async def get_all_userevents():
    logging.info("Received request to fetch all userevents.")
    try:
        docs = await Userevent.find_all().to_list()
        logging.info(f"Fetched {len(docs)} userevent(s) successfully.")
    except Exception as e:
        logging.exception("Failed to fetch all userevents.")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    return docs

# GET ONE BY ID
@router.get('/{item_id}', response_model=UsereventRead)
async def get_userevent(item_id: str):
    logging.info(f"Received request to fetch userevent with _id: {item_id}")
    try:
        doc = await Userevent.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Userevent with _id {item_id} not found.")
            raise HTTPException(status_code=404, detail='Userevent not found')
        logging.info(f"Fetched userevent with _id: {item_id} successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to fetch Userevent with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    return doc

# UPDATE
@router.put('/{item_id}', response_model=UsereventRead)
async def update_userevent(item_id: str, item: UsereventCreate):
    logging.info(f"Received request to update userevent with _id: {item_id}")
    try:
        doc = await Userevent.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Userevent with _id {item_id} not found for update.")
            raise HTTPException(status_code=404, detail='Userevent not found')
        update_data = item.dict(exclude_unset=True)
        # Optionally prevent updating base fields:
        update_data.pop('_id', None)
        update_data.pop('createdAt', None)
        # For updatedAt, BaseEntity.save() will update it automatically.
        for key, value in update_data.items():
            setattr(doc, key, value)
        await doc.save()
        logging.info(f"Userevent with _id {item_id} updated successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to update Userevent with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    return doc

# DELETE
@router.delete('/{item_id}')
async def delete_userevent(item_id: str):
    logging.info(f"Received request to delete userevent with _id: {item_id}")
    try:
        doc = await Userevent.get(PydanticObjectId(item_id))
        if not doc:
            logging.warning(f"Userevent with _id {item_id} not found for deletion.")
            raise HTTPException(status_code=404, detail='Userevent not found')
        await doc.delete()
        logging.info(f"Userevent with _id {item_id} deleted successfully.")
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception(f"Failed to delete Userevent with _id: {item_id}")
        raise HTTPException(status_code=500, detail='Internal Server Error')
    return {'message': 'Userevent deleted successfully'}