from fastapi import APIRouter, HTTPException
from typing import List
from app.models.account_model import Account, AccountCreate, AccountUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

router = APIRouter()

@router.get("", response_model=List[Account])
async def list_accounts() -> List[Account]:
    """List all accounts"""
    accounts = await Account.find_all()
    return list(accounts)  # Convert Sequence to List

@router.get("/{account_id}", response_model=Account)
async def get_account(account_id: str) -> Account:
    """Get a specific account by ID"""
    account = await Account.get(account_id)
    if not account:
        raise NotFoundError("Account", account_id)
    return account

@router.post("", response_model=Account)
async def create_account(account_data: AccountCreate) -> Account:
    """Create a new account"""
    account = Account(**account_data.model_dump())
    return await account.save()

@router.put("/{account_id}", response_model=Account)
async def update_account(account_id: str, account_data: AccountUpdate) -> Account:
    """Update an existing account"""
    # Check if account exists
    existing = await Account.get(account_id)
    if not existing:
        raise NotFoundError("Account", account_id)
    
    # Update fields
    account = Account(**account_data.model_dump())
    account.id = account_id
    account.createdAt = existing.createdAt
    
    # Save changes
    return await account.save()

@router.delete("/{account_id}")
async def delete_account(account_id: str):
    """Delete an account by ID."""
    try:
        account = await Account.get(account_id)
        if not account:
            raise NotFoundError("Account", account_id)
        await account.delete()
        return {"message": "Account deleted successfully"}
    except NotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "message": str(e),
                "error_type": "not_found",
                "context": {
                    "id": account_id
                }
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred while deleting the account",
                "error_type": "internal_error",
                "context": {"error": str(e)}
            }
        )

@router.get("/metadata")
async def get_account_metadata():
    """Get metadata for Account entity."""
    return Account.get_metadata()