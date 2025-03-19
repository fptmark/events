import sys
import pytest
import random
import string
import asyncio
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

@pytest.mark.asyncio
async def test_create_account_and_user():
    print("*** starting test for account and user creation")
    config = load_config()
    await Database.init(config['mongo_uri'], config['db_name'])
    db = Database.get_db()
    
    # Verify database connection by counting existing Account documents.
    existing_accounts = await db['account'].find().to_list(None)
    print(f"Number of accounts in the database: {len(existing_accounts)}")
    sys.stdout.flush()
    
    # Create an Account.
    account_data = AccountCreate(expiredAt=None)
    account = Account(**account_data.dict(exclude_unset=True))
    await account.save()
    assert account.id is not None, "Account.id should be generated"
    print(f"account.id = {account.id}.  Type = {type(account.id)}")
    
    # Create a User referencing the Account.
    gen_email = generate_random_email()
    gen_username = generate_random_username()
    user_data = UserCreate(
        accountId=account.id,
        username=gen_username,
        email=gen_email,
        password="password123",
        firstName="Test",
        lastName="User",
        gender="male",
        isAccountOwner=True
    )
    user = User(**user_data.dict(exclude_unset=True))
    await user.save()

    # Retrieve the user from the database.
    fetched_user = await User.get(user.id)
    assert fetched_user is not None, "User should be found in the database"
    assert fetched_user.accountId == account.id, "User's accountId should match the created Account's _id"
    print(f"Fetched user: {fetched_user}")
