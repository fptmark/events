import sys
import asyncio
import random
import string
from app.models.account_model import Account, AccountCreate
from app.models.user_model import User, UserCreate
from app.utilities.config import load_config 
from app.db import Database

def generate_random_email():
    rand_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"{rand_str}@example.com"

def generate_random_username():
    rand_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"user_{rand_str}"

async def create_user():
    admin_input = input("Is this new user an admin? (y/n): ").strip().lower()
    is_admin = admin_input == 'y'
    
    gen_email = generate_random_email()
    override_email = input(f"Press Enter to accept the email [{gen_email}], or type an override: ").strip()
    email = override_email if override_email else gen_email

    gen_username = generate_random_username()
    override_username = input(f"Press Enter to accept the username [{gen_username}], or type an override: ").strip()
    username = override_username if override_username else gen_username

    default_gender = 'male'
    override_gender = input(f"Press Enter to accept the gender [{default_gender}], or type an override: ").strip()
    gender = override_gender if override_gender else default_gender

    first_name = input("Enter first name [Test]: ").strip() or "Test"
    last_name = input("Enter last name [User]: ").strip() or "User"
    password = input("Enter password [password123]: ").strip() or "password123"

    if is_admin:
        print("Creating a new account for admin user...")
        account_data = AccountCreate(expiredAt=None)
        account = Account(**account_data.dict(exclude_unset=True))
        await account.save()
        account_id = account.id
        print(f"New account created with id: {account_id}")
    else:
        print("Fetching existing admin users...")
        db = Database.get_db()
        admin_users = await db['user'].find({"isAccountOwner": True}).to_list(None)
        if not admin_users:
            print("No admin users found. Cannot associate account.")
            return
        print("Select an admin user by number:")
        for idx, admin in enumerate(admin_users, start=1):
            print(f"{idx}: {admin.get('username', 'N/A')} (Account: {admin.get('accountId')})")
        choice = input("Enter the number of the admin to associate with: ").strip()
        try:
            idx = int(choice) - 1
            chosen_admin = admin_users[idx]
            account_id = chosen_admin.get("accountId")
            print(f"Using account id {account_id} from admin user {chosen_admin.get('username')}.")
        except (ValueError, IndexError):
            print("Invalid selection. Aborting create operation.")
            return

    user_data = UserCreate(
        accountId=account_id,
        username=username,
        email=email,
        password=password,
        firstName=first_name,
        lastName=last_name,
        gender=gender,
        isAccountOwner=is_admin
    )
    user = User(**user_data.dict(exclude_unset=True))
    await user.save()
    print(f"User created with id: {user.id}")

async def read_user():
    user_id = input("Enter the user id to fetch: ").strip()
    user = await User.get(user_id)
    if user:
        print("User details:")
        print(user)
    else:
        print("User not found.")

async def update_user():
    user_id = input("Enter the user id to update: ").strip()
    user = await User.get(user_id)
    if not user:
        print("User not found.")
        return
    print("Leave fields blank to keep current values.")
    new_email = input(f"Email [{user.email}]: ").strip() or user.email
    new_username = input(f"Username [{user.username}]: ").strip() or user.username
    new_first_name = input(f"First name [{user.firstName}]: ").strip() or user.firstName
    new_last_name = input(f"Last name [{user.lastName}]: ").strip() or user.lastName
    new_gender = input(f"Gender [{user.gender}]: ").strip() or user.gender

    user.email = new_email
    user.username = new_username
    user.firstName = new_first_name
    user.lastName = new_last_name
    user.gender = new_gender
    await user.save()
    print("User updated.")

async def list_users(return_list=False):
    db = Database.get_db()
    users = await db['user'].find().to_list(None)
    if not users:
        print("No users found.")
    else:
        print("Listing all users:")
        for idx, user in enumerate(users, start=1):
            user_id = user.get("id") or user.get("_id")
            print(f"{idx}: ID: {user_id}, Username: {user.get('username')}, Account: {user.get('accountId')}")
    if return_list:
        return users

async def delete_user():
    users = await list_users(return_list=True)
    if not users:
        return

    selection = input("Enter the number or range (e.g. 3 or 3-5) of the user(s) to delete: ").strip()
    selected_indices = []
    if '-' in selection:
        try:
            start_str, end_str = selection.split('-', 1)
            start = int(start_str)
            end = int(end_str)
            if start < 1 or end > len(users) or start > end:
                print("Invalid range.")
                return
            selected_indices = list(range(start, end + 1))
        except ValueError:
            print("Invalid input. Please provide a valid number or range.")
            return
    else:
        try:
            num = int(selection)
            if num < 1 or num > len(users):
                print("Invalid number.")
                return
            selected_indices = [num]
        except ValueError:
            print("Invalid input. Please provide a valid number or range.")
            return

    for idx in selected_indices:
        user_dict = users[idx - 1]
        user_id = user_dict.get("id") or user_dict.get("_id")
        try:
            user_instance = await User.get(user_id)
            if not user_instance:
                print(f"User with id {user_id} not found.")
                continue
            confirmation = input(f"Are you sure you want to delete user {user_dict.get('username')}? (y/n): ").strip().lower()
            if confirmation == 'y':
                await user_instance.delete()
                print(f"User {user_dict.get('username')} deleted.")
            else:
                print(f"Skipped deletion for user {user_dict.get('username')}.")
        except Exception as e:
            print(f"Error deleting user {user_dict.get('username')}: {e}")
