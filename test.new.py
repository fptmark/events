import sys
import asyncio
import random
import string
from app.models.account_model import Account, AccountCreate, AccountRead
from app.models.user_model import User, UserCreate, UserRead
from app.utilities.config import load_config 
from app.db import Database

def generate_random_email():
    """Generate a random email address."""
    rand_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"{rand_str}@example.com"

def generate_random_username():
    """Generate a random username."""
    rand_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"user_{rand_str}"

async def create_user():
    # Prompt for whether the new user is an admin.
    admin_input = input("Is this new user an admin? (y/n): ").strip().lower()
    is_admin = admin_input == 'y'
    
    # For creating a user, supply defaults with prompts.
    # Email
    gen_email = generate_random_email()
    override_email = input(f"Press Enter to accept the email [{gen_email}], or type an override: ").strip()
    email = override_email if override_email else gen_email

    # Username
    gen_username = generate_random_username()
    override_username = input(f"Press Enter to accept the username [{gen_username}], or type an override: ").strip()
    username = override_username if override_username else gen_username

    # Gender with default
    default_gender = 'male'
    override_gender = input(f"Press Enter to accept the gender [{default_gender}], or type an override: ").strip()
    gender = override_gender if override_gender else default_gender

    # First Name
    first_name = input("Enter first name [Test]: ").strip() or "Test"
    # Last Name
    last_name = input("Enter last name [User]: ").strip() or "User"
    # Password (in a real system you would hash this)
    password = input("Enter password [password123]: ").strip() or "password123"

    if is_admin:
        # Create a new account for an admin user.
        print("Creating a new account for admin user...")
        account_data = AccountCreate(expiredAt=None)
        account = Account(**account_data.dict(exclude_unset=True))
        await account.save()
        account_id = account.id
        print(f"New account created with id: {account_id}")
    else:
        # For non-admin users, list all admin users (isAccountOwner==True) so that one can be selected.
        print("Fetching existing admin users...")
        db = Database.get_db()
        # Assuming that admin users have isAccountOwner True
        admin_users = await db['user'].find({"isAccountOwner": True}).to_list(None)
        if not admin_users:
            print("No admin users found. Cannot associate account.")
            return
        print("Select an admin user by number:")
        for idx, admin in enumerate(admin_users):
            print(f"{idx}: {admin.get('username', 'N/A')} (Account: {admin.get('accountId')})")
        choice = input("Enter the number of the admin to associate with: ").strip()
        try:
            idx = int(choice)
            chosen_admin = admin_users[idx]
            account_id = chosen_admin.get("accountId")
            print(f"Using account id {account_id} from admin user {chosen_admin.get('username')}.")
        except (ValueError, IndexError):
            print("Invalid selection. Aborting create operation.")
            return

    # Create the user
    if account_id:
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
    # In a full implementation, you'd also allow updating the password, etc.
    
    # Assuming the user model has an update method.
    user.email = new_email
    user.username = new_username
    user.firstName = new_first_name
    user.lastName = new_last_name
    user.gender = new_gender
    await user.save()  # Or user.update() if that's your API.
    print("User updated.")

async def delete_user():
    user_id = input("Enter the user id to delete: ").strip()
    user = await User.get(user_id)
    if not user:
        print("User not found.")
        return
    confirmation = input(f"Are you sure you want to delete user {user.username}? (y/n): ").strip().lower()
    if confirmation == 'y':
        await user.delete()  # Assuming a delete() method exists.
        print("User deleted.")
    else:
        print("Deletion cancelled.")

async def list_users():
    db = Database.get_db()
    users = await db['user'].find().to_list(None)
    if not users:
        print("No users found.")
    else:
        print("Listing all users:")
        for user in users:
            print(f"ID: {user.get('id', user.get('_id'))}, Username: {user.get('username')}, Account: {user.get('accountId')}")

async def main():
    print("*** Starting the User Management CLI ***")
    config = load_config()
    await Database.init(config['mongo_uri'], config['db_name'])
    # Main loop
    while True:
        print("\nChoose an operation:")
        print("1: Create User")
        print("2: Read User")
        print("3: Update User")
        print("4: Delete User")
        print("5: List Users")
        print("6: Exit")
        choice = input("Enter your choice: ").strip()
        if choice == '1':
            await create_user()
        elif choice == '2':
            await read_user()
        elif choice == '3':
            await update_user()
        elif choice == '4':
            await delete_user()
        elif choice == '5':
            await list_users()
        elif choice == '6':
            print("Exiting CLI.")
            break
        else:
            print("Invalid choice. Please try again.")
        # Ensure output is flushed for interactive prompt.
        sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())
