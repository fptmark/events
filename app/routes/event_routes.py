from fastapi import APIRouter, HTTPException
from typing import List
from app.models.event_model import Event
from app.utils.db import get_db
from bson import ObjectId

router = APIRouter()

# CRUD Operations
@router.post('/', response_model=Event)
async def create_event(item: Event):
    db = get_db()
    item_dict = item.dict()
    item_dict['_id'] = str(ObjectId())
    await db['events'].insert_one(item_dict)
    return item_dict

@router.get('/', response_model=List[Event])
async def get_all_events():
    db = get_db()
    items = await db['events'].find().to_list(None)
    return items

@router.get('/{item_id}', response_model=Event)
async def get_event(item_id: str):
    db = get_db()
    item = await db['events'].find_one({'_id': ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail='Event not found')
    return item

@router.put('/{item_id}', response_model=Event)
async def update_event(item_id: str, item: Event):
    db = get_db()
    result = await db['events'].update_one({'_id': ObjectId(item_id)}, {'$set': item.dict()})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail='Event not found')
    return item

@router.delete('/{item_id}')
async def delete_event(item_id: str):
    db = get_db()
    result = await db['events'].delete_one({'_id': ObjectId(item_id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail='Event not found')
    return {'message': 'Event deleted successfully'}
