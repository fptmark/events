from fastapi import APIRouter, HTTPException
from typing import List
from app.models.userevent_model import UserEvent
from app.utils.db import get_db
from bson import ObjectId

router = APIRouter()

# CRUD Operations
@router.post('/', response_model=UserEvent)
async def create_userevent(item: UserEvent):
    db = get_db()
    item_dict = item.dict()
    item_dict['_id'] = str(ObjectId())
    await db['userevents'].insert_one(item_dict)
    return item_dict

@router.get('/', response_model=List[UserEvent])
async def get_all_userevents():
    db = get_db()
    items = await db['userevents'].find().to_list(None)
    return items

@router.get('/{item_id}', response_model=UserEvent)
async def get_userevent(item_id: str):
    db = get_db()
    item = await db['userevents'].find_one({'_id': ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail='UserEvent not found')
    return item

@router.put('/{item_id}', response_model=UserEvent)
async def update_userevent(item_id: str, item: UserEvent):
    db = get_db()
    result = await db['userevents'].update_one({'_id': ObjectId(item_id)}, {'$set': item.dict()})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail='UserEvent not found')
    return item

@router.delete('/{item_id}')
async def delete_userevent(item_id: str):
    db = get_db()
    result = await db['userevents'].delete_one({'_id': ObjectId(item_id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail='UserEvent not found')
    return {'message': 'UserEvent deleted successfully'}
