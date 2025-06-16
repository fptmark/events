from fastapi import APIRouter
from typing import List
import logging
from app.models.account_model import Account, AccountCreate, AccountUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[Account])
async def list_accounts() -> List[Account]:
    """List all accounts"""
    try:
        logger.info("Fetching all accounts")
        accounts, validation_errors = await Account.find_all()
        records = len(accounts)
        logger.info(f"Retrieved {records} accounts")
        return list(accounts)
    except Exception as e:
        logger.error(f"Error listing accounts: {e}")
        raise


@router.get("/{account_id}", response_model=Account)
async def get_account(account_id: str) -> Account:
    """Get a specific account by ID"""
    try:
        logger.info(f"Fetching account with ID: {account_id }")
        account = await Account.get(account_id)
        logger.info(f"Retrieved account: {account.id }")
        return account
    except NotFoundError:
        logger.warning(f"Account not found: {account_id }")
        raise
    except Exception as e:
        logger.error(f"Error getting account {account_id }: {e}")
        raise


@router.post("", response_model=Account)
async def create_account(account_data: AccountCreate) -> Account:
    """Create a new account"""
    try:
        logger.info(f"Creating account with data: {account_data }")
        account = Account(**account_data.model_dump())
        result = await account.save()
        logger.info(f"Account created successfully with ID: {result.id}")
        return result
    except (ValidationError, DuplicateError) as e:
        logger.warning(f"Validation error creating account: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise


@router.put("/{account_id}", response_model=Account)
async def update_account(account_id: str, account_data: AccountUpdate) -> Account:
    """Update an existing account"""
    try:
        logger.info(f"Updating account {account_id } with data: {account_data }")

        existing = await Account.get(account_id)
        logger.info(f"Found existing account: {existing.id}")

        account = Account(**account_data.model_dump())
        result = await account.save(account_id)
        logger.info(f"Account updated successfully: {result.id}")
        return result
    except (NotFoundError, ValidationError, DuplicateError) as e:
        logger.warning(f"Error updating account {account_id}: {type(e).__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating account {account_id}: {e}")
        raise


@router.delete("/{account_id}")
async def delete_account(account_id: str):
    """Delete a account"""
    try:
        logger.info(f"Deleting account: {account_id}")
        account = await Account.get(account_id)
        await account.delete()
        logger.info(f"Account deleted successfully: {account_id}")
        return {"message": "Account deleted successfully"}
    except NotFoundError:
        logger.warning(f"Account not found for deletion: {account_id}")
        raise