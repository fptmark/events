import sys
import asyncio
from user import create_user, read_user, update_user, delete_user, list_users
from account import list_accounts, delete_account
from app.utilities.config import load_config 
from app.db import Database

async def main():
    # Initialize the database
    config = load_config()
    await Database.init(config['mongo_uri'], config['db_name'])
    
    while True:
        print("\n=== Main Menu ===")
        print("1: User Management")
        print("2: Account Management")
        print("3: Exit")
        choice = input("Enter your choice: ").strip()
        
        if choice == '1':
            # User management sub-menu
            print("\n--- User Management ---")
            print("1: Create User")
            print("2: Read User")
            print("3: Update User")
            print("4: Delete User")
            print("5: List Users")
            sub_choice = input("Enter your choice: ").strip()
            if sub_choice == '1':
                await create_user()
            elif sub_choice == '2':
                await read_user()
            elif sub_choice == '3':
                await update_user()
            elif sub_choice == '4':
                await delete_user()
            elif sub_choice == '5':
                await list_users()
            else:
                print("Invalid user management option.")
        
        elif choice == '2':
            # Account management sub-menu
            print("\n--- Account Management ---")
            print("1: List Accounts (with their users)")
            print("2: Delete Account (cascade deletes associated users)")
            sub_choice = input("Enter your choice: ").strip()
            if sub_choice == '1':
                await list_accounts()
            elif sub_choice == '2':
                await delete_account()
            else:
                print("Invalid account management option.")
        
        elif choice == '3':
            print("Exiting CLI.")
            break
        
        else:
            print("Invalid choice. Please try again.")
        sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())
