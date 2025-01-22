from fastapi import APIRouter, HTTPException
from typing import List
from app.models.profile_model import Profile
from app.utils.db import get_db
from bson import ObjectId

router = APIRouter()

# CRUD Operations
@router.post('/', response_model=Profile)
async def create_profile(item: Profile):
    db = get_db()
    item_dict = item.dict()
    item_dict['_id'] = str(ObjectId())
    await db['profiles'].insert_one(item_dict)
    return item_dict

@router.get('/', response_model=List[Profile])
async def get_all_profiles():
    db = get_db()
    items = await db['profiles'].find().to_list(None)
    return items

@router.get('/{item_id}', response_model=Profile)
async def get_profile(item_id: str):
    db = get_db()
    item = await db['profiles'].find_one({'_id': ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail='Profile not found')
    return item

@router.put('/{item_id}', response_model=Profile)
async def update_profile(item_id: str, item: Profile):
    db = get_db()
    result = await db['profiles'].update_one({'_id': ObjectId(item_id)}, {'$set': item.dict()})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail='Profile not found')
    return item

@router.delete('/{item_id}')
async def delete_profile(item_id: str):
    db = get_db()
    result = await db['profiles'].delete_one({'_id': ObjectId(item_id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail='Profile not found')
    return {'message': 'Profile deleted successfully'}
