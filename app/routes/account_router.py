from fastapi import APIRouter
from typing import List, Dict, Any
import logging
from app.models.account_model import Account, AccountCreate, AccountUpdate
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError
from app.notification import NotificationManager, notify_success, notify_info, notify_error, NotificationType

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def list_accounts() -> Dict[str, Any]:
    """List all accounts"""
    notifications = NotificationManager().start_operation("list_accounts", "Account")
    
    try:
        notify_info("Fetching all accounts", NotificationType.SYSTEM)
        accounts, validation_errors = await Account.get_all()
        records = len(accounts)
        notify_success(f"Retrieved {records} accounts", NotificationType.SYSTEM)
        
        return {
            "data": [account.model_dump() for account in accounts],
            "notifications": notifications.to_dict()
        }
    except Exception as e:
        notify_error(f"Error listing accounts: {e}", NotificationType.SYSTEM)
        raise
    finally:
        NotificationManager().end_operation()


@router.get("/{account_id}")
async def get_account(account_id: str) -> Dict[str, Any]:
    """Get a specific account by ID"""
    notifications = NotificationManager().start_operation("get_account", "Account")
    
    try:
        notify_info(f"Fetching account with ID: {account_id}", NotificationType.SYSTEM)
        account = await Account.get(account_id)
        notify_success(f"Retrieved account: {account.id}", NotificationType.SYSTEM)
        
        return {
            "data": account.model_dump(),
            "notifications": notifications.to_dict()
        }
    except NotFoundError:
        notify_error(f"Account not found: {account_id}", NotificationType.BUSINESS)
        raise
    except Exception as e:
        notify_error(f"Error getting account {account_id}: {e}", NotificationType.SYSTEM)
        raise
    finally:
        NotificationManager().end_operation()


@router.post("")
async def create_account(account_data: AccountCreate) -> Dict[str, Any]:
    """Create a new account"""
    notifications = NotificationManager().start_operation("create_account", "Account")
    
    try:
        notify_info("Creating new account", NotificationType.BUSINESS)
        account = Account(**account_data.model_dump())
        result = await account.save()
        notify_success(f"Account created successfully with ID: {result.id}", NotificationType.BUSINESS)
        
        return {
            "data": result.model_dump(),
            "notifications": notifications.to_dict()
        }
    except (ValidationError, DuplicateError) as e:
        notify_error(f"Validation error creating account: {type(e).__name__}: {str(e)}", NotificationType.VALIDATION)
        raise
    except Exception as e:
        notify_error(f"Error creating account: {e}", NotificationType.SYSTEM)
        raise
    finally:
        NotificationManager().end_operation()


@router.put("/{account_id}")
async def update_account(account_id: str, account_data: AccountUpdate) -> Dict[str, Any]:
    """Update an existing account"""
    notifications = NotificationManager().start_operation("update_account", "Account")
    
    try:
        notify_info(f"Updating account {account_id}", NotificationType.BUSINESS)

        existing = await Account.get(account_id)
        notify_info(f"Found existing account: {existing.id}", NotificationType.SYSTEM)

        account = Account(**account_data.model_dump())
        result = await account.save(account_id)
        notify_success(f"Account updated successfully: {result.id}", NotificationType.BUSINESS)
        
        return {
            "data": result.model_dump(),
            "notifications": notifications.to_dict()
        }
    except (NotFoundError, ValidationError, DuplicateError) as e:
        notify_error(f"Error updating account {account_id}: {type(e).__name__}: {str(e)}", NotificationType.VALIDATION)
        raise
    except Exception as e:
        notify_error(f"Error updating account {account_id}: {e}", NotificationType.SYSTEM)
        raise
    finally:
        NotificationManager().end_operation()


@router.delete("/{account_id}")
async def delete_account(account_id: str) -> Dict[str, Any]:
    """Delete a account"""
    notifications = NotificationManager().start_operation("delete_account", "Account")
    
    try:
        notify_info(f"Deleting account: {account_id}", NotificationType.BUSINESS)
        account = await Account.get(account_id)
        await account.delete()
        notify_success(f"Account deleted successfully: {account_id}", NotificationType.BUSINESS)
        
        return {
            "message": "Account deleted successfully",
            "notifications": notifications.to_dict()
        }
    except NotFoundError:
        notify_error(f"Account not found for deletion: {account_id}", NotificationType.BUSINESS)
        raise
    except Exception as e:
        notify_error(f"Error deleting account {account_id}: {e}", NotificationType.SYSTEM)
        raise
    finally:
        NotificationManager().end_operation()