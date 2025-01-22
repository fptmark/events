from fastapi import APIRouter, HTTPException
from typing import List
from app.models.url_model import URL
from app.utils.db import get_db
from bson import ObjectId

router = APIRouter()

# CRUD Operations
@router.post('/', response_model=URL)
async def create_url(item: URL):
    db = get_db()
    item_dict = item.dict()
    item_dict['_id'] = str(ObjectId())
    await db['urls'].insert_one(item_dict)
    return item_dict

@router.get('/', response_model=List[URL])
async def get_all_urls():
    db = get_db()
    items = await db['urls'].find().to_list(None)
    return items

@router.get('/{item_id}', response_model=URL)
async def get_url(item_id: str):
    db = get_db()
    item = await db['urls'].find_one({'_id': ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail='URL not found')
    return item

@router.put('/{item_id}', response_model=URL)
async def update_url(item_id: str, item: URL):
    db = get_db()
    result = await db['urls'].update_one({'_id': ObjectId(item_id)}, {'$set': item.dict()})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail='URL not found')
    return item

@router.delete('/{item_id}')
async def delete_url(item_id: str):
    db = get_db()
    result = await db['urls'].delete_one({'_id': ObjectId(item_id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail='URL not found')
    return {'message': 'URL deleted successfully'}
