from fastapi import APIRouter, HTTPException
from typing import List
from app.models.account_model import Account
from app.utils.db import get_db
from bson import ObjectId

router = APIRouter()

# CRUD Operations
@router.post('/', response_model=Account)
async def create_account(item: Account):
    db = get_db()
    item_dict = item.dict()
    item_dict['_id'] = str(ObjectId())
    await db['accounts'].insert_one(item_dict)
    return item_dict

@router.get('/', response_model=List[Account])
async def get_all_accounts():
    db = get_db()
    items = await db['accounts'].find().to_list(None)
    return items

@router.get('/{item_id}', response_model=Account)
async def get_account(item_id: str):
    db = get_db()
    item = await db['accounts'].find_one({'_id': ObjectId(item_id)})
    if not item:
        raise HTTPException(status_code=404, detail='Account not found')
    return item

@router.put('/{item_id}', response_model=Account)
async def update_account(item_id: str, item: Account):
    db = get_db()
    result = await db['accounts'].update_one({'_id': ObjectId(item_id)}, {'$set': item.dict()})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail='Account not found')
    return item

@router.delete('/{item_id}')
async def delete_account(item_id: str):
    db = get_db()
    result = await db['accounts'].delete_one({'_id': ObjectId(item_id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail='Account not found')
    return {'message': 'Account deleted successfully'}
