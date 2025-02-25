import sys
import asyncio
from app.models.account_model import Account
from app.models.user_model import User
from app.db import Database

async def list_accounts(return_list=False):
    db = Database.get_db()
    accounts = await db['account'].find().to_list(None)
    if not accounts:
        print("No accounts found.")
    else:
        print("Listing all accounts and their users:")
        for idx, account in enumerate(accounts, start=1):
            account_id = account.get("id") or account.get("_id")
            # Fetch users for this account
            users = await db['user'].find({"accountId": account_id}).to_list(None)

            print(f"{idx}: Account ID: {account_id} has {len(users)} user(s)")

            if users:
                for user in users:
                    user_id = user.get("id") or user.get("_id")
                    print(f"    User: {user.get('username')} (ID: {user_id})")
            # else:
                # print("    No users found for this account.")
    if return_list:
        return accounts

async def delete_account():
    accounts = await list_accounts(return_list=True)
    if not accounts:
        return

    selection = input("Enter the number or range (e.g. 1 or 1-2) of the account(s) to delete: ").strip()
    selected_indices = []
    if '-' in selection:
        try:
            start_str, end_str = selection.split('-', 1)
            start = int(start_str)
            end = int(end_str)
            if start < 1 or end > len(accounts) or start > end:
                print("Invalid range.")
                return
            selected_indices = list(range(start, end + 1))
        except ValueError:
            print("Invalid input. Please provide a valid number or range.")
            return
    else:
        try:
            num = int(selection)
            if num < 1 or num > len(accounts):
                print("Invalid number.")
                return
            selected_indices = [num]
        except ValueError:
            print("Invalid input. Please provide a valid number or range.")
            return

    db = Database.get_db()
    for idx in selected_indices:
        account = accounts[idx - 1]
        account_id = account.get("id") or account.get("_id")
        users = await db['user'].find({"accountId": account_id}).to_list(None)
        try:
            confirmation = input(f"Are you sure you want to delete account {account_id} and all its users? (y/n): ").strip().lower() if len(users) > 0 else 'y' 
            if confirmation == 'y':
                # Delete all users associated with this account
                for user in users:
                    user_id = user.get("id") or user.get("_id")
                    user_instance = await User.get(user_id)
                    if user_instance:
                        await user_instance.delete()
                        print(f"Deleted user {user.get('username')}.")
                # Delete the account itself
                account_instance = await Account.get(account_id)
                if account_instance:
                    await account_instance.delete()
                    print(f"Account {account_id} deleted.")
                else:
                    print(f"Account {account_id} not found.")
            else:
                print("Skipped deletion for this account.")
        except Exception as e:
            print(f"Error deleting account {account_id}: {e}")
