from fastapi import APIRouter, HTTPException
from typing import List
from app.models.tagaffinity_model import TagAffinity
from app.utils.db import get_db
from bson import ObjectId

router = APIRouter()

# CRUD Operations
@router.post('/', response_model=TagAffinity)
async def create_tagaffinity(item: TagAffinity):
    db = get_db()
    item_dict = item.dict()
    item_dict['_id'] = str(ObjectId())
    await db['tagaffinitys'].insert_one(item_dict)
    return item_dict

@router.get('/', response_model=List[TagAffinity])
async def get_all_tagaffinitys():
    db = get_db()
    items = await db['tagaffinitys'].find().to_list(None)
    return items

@router.get('/{item_id}', response_model=TagAffinity)
async def get_tagaffinity(item_id: str):
    db = get_db()
    item = await db['tagaffinitys'].find_one({'_id': ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail='TagAffinity not found')
    return item

@router.put('/{item_id}', response_model=TagAffinity)
async def update_tagaffinity(item_id: str, item: TagAffinity):
    db = get_db()
    result = await db['tagaffinitys'].update_one({'_id': ObjectId(item_id)}, {'$set': item.dict()})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail='TagAffinity not found')
    return item

@router.delete('/{item_id}')
async def delete_tagaffinity(item_id: str):
    db = get_db()
    result = await db['tagaffinitys'].delete_one({'_id': ObjectId(item_id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail='TagAffinity not found')
    return {'message': 'TagAffinity deleted successfully'}
