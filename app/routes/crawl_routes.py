from fastapi import APIRouter, HTTPException
from typing import List
from app.models.crawl_model import Crawl
from app.utils.db import get_db
from bson import ObjectId

router = APIRouter()

# CRUD Operations
@router.post('/', response_model=Crawl)
async def create_crawl(item: Crawl):
    db = get_db()
    item_dict = item.dict()
    item_dict['_id'] = str(ObjectId())
    await db['crawls'].insert_one(item_dict)
    return item_dict

@router.get('/', response_model=List[Crawl])
async def get_all_crawls():
    db = get_db()
    items = await db['crawls'].find().to_list(None)
    return items

@router.get('/{item_id}', response_model=Crawl)
async def get_crawl(item_id: str):
    db = get_db()
    item = await db['crawls'].find_one({'_id': ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail='Crawl not found')
    return item

@router.put('/{item_id}', response_model=Crawl)
async def update_crawl(item_id: str, item: Crawl):
    db = get_db()
    result = await db['crawls'].update_one({'_id': ObjectId(item_id)}, {'$set': item.dict()})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail='Crawl not found')
    return item

@router.delete('/{item_id}')
async def delete_crawl(item_id: str):
    db = get_db()
    result = await db['crawls'].delete_one({'_id': ObjectId(item_id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail='Crawl not found')
    return {'message': 'Crawl deleted successfully'}
