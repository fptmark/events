import sys
import asyncio
import random
import string
import requests
import argparse
from typing import List, Dict, Any
from collections import defaultdict

# Configuration
API_BASE_URL = "http://localhost:5500/api"

# Track created entities for potential removal
created_entities = defaultdict(list)  # {table_name: [ids]}

def generate_random_email() -> str:
    """Generate a random valid email address"""
    rand_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"{rand_str}@example.com"

def generate_random_username() -> str:
    """Generate a random username"""
    rand_str = ''.join(random.choices(string.ascii_lowercase, k=6))
    return f"user_{rand_str}"

def create_account() -> str:
    """Create an account via API and return its ID"""
    response = requests.post(f"{API_BASE_URL}/account", json={})
    response.raise_for_status()
    account_id = response.json()["_id"]
    created_entities["account"].append(account_id)
    return account_id

def remove_created_entities():
    """Remove all entities created during this execution"""
    # Remove in reverse order of creation to handle dependencies
    tables = ["user", "account"]  # Order matters: remove dependent entities first
    
    for table in tables:
        if table in created_entities:
            print(f"\nRemoving {len(created_entities[table])} {table} entities...")
            for entity_id in created_entities[table]:
                try:
                    response = requests.delete(f"{API_BASE_URL}/{table}/{entity_id}")
                    if response.status_code == 200:
                        print(f"✓ Removed {table} {entity_id}")
                    else:
                        print(f"✗ Failed to remove {table} {entity_id}: {response.text}")
                except requests.exceptions.RequestException as e:
                    print(f"✗ Error removing {table} {entity_id}: {str(e)}")

def test_user_creation(account_id: str) -> List[str]:
    """Run test cases for user creation via API and return error messages"""
    errors = []
    
    # Test Case 1: Valid user creation (baseline)
    try:
        user_data = {
            "accountId": account_id,
            "username": generate_random_username(),
            "email": generate_random_email(),
            "password": "password123",
            "firstName": "Test",
            "lastName": "User",
            "gender": "male",
            "isAccountOwner": False
        }
        response = requests.post(f"{API_BASE_URL}/user", json=user_data)
        response.raise_for_status()
        user_id = response.json()["_id"]
        created_entities["user"].append(user_id)
        print(f"✓ Successfully created valid user: {user_id}")
    except requests.exceptions.RequestException as e:
        errors.append(f"✗ Valid user creation failed: {str(e)}")

    # Test Case 2: Duplicate email
    try:
        duplicate_email = generate_random_email()
        # Create first user
        user1_data = {
            "accountId": account_id,
            "username": generate_random_username(),
            "email": duplicate_email,
            "password": "password123",
            "firstName": "Test",
            "lastName": "User",
            "gender": "male",
            "isAccountOwner": False
        }
        response = requests.post(f"{API_BASE_URL}/user", json=user1_data)
        response.raise_for_status()
        user_id = response.json()["_id"]
        created_entities["user"].append(user_id)
        
        # Try to create second user with same email
        user2_data = {
            "accountId": account_id,
            "username": generate_random_username(),
            "email": duplicate_email,
            "password": "password123",
            "firstName": "Test",
            "lastName": "User",
            "gender": "male",
            "isAccountOwner": False
        }
        response = requests.post(f"{API_BASE_URL}/user", json=user2_data)
        if response.status_code == 200:
            user_id = response.json()["_id"]
            created_entities["user"].append(user_id)
            errors.append("✗ Duplicate email constraint failed: Created user with duplicate email")
        else:
            print(f"✓ Successfully caught duplicate email: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✓ Successfully caught duplicate email: {str(e)}")

    # Test Case 3: Required fields missing
    required_field_tests = [
        {"email": None, "username": generate_random_username()},
        {"email": generate_random_email(), "username": None},
        {"email": "", "username": generate_random_username()},
        {"email": generate_random_email(), "username": ""}
    ]
    
    for test in required_field_tests:
        try:
            user_data = {
                "accountId": account_id,
                "username": test["username"],
                "email": test["email"],
                "password": "password123",
                "firstName": "Test",
                "lastName": "User",
                "gender": "male",
                "isAccountOwner": False
            }
            response = requests.post(f"{API_BASE_URL}/user", json=user_data)
            if response.status_code == 200:
                errors.append(f"✗ Required field validation failed: Created user with {test}")
            else:
                print(f"✓ Successfully caught missing required field: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"✓ Successfully caught missing required field: {str(e)}")

    # Test Case 4: Invalid email format
    invalid_emails = [
        "not.an.email",
        "missing@domain",
        "@nodomain.com",
        "spaces in@email.com",
        "special#chars@domain.com"
    ]
    
    for email in invalid_emails:
        try:
            user_data = {
                "accountId": account_id,
                "username": generate_random_username(),
                "email": email,
                "password": "password123",
                "firstName": "Test",
                "lastName": "User",
                "gender": "male",
                "isAccountOwner": False
            }
            response = requests.post(f"{API_BASE_URL}/user", json=user_data)
            if response.status_code == 200:
                errors.append(f"✗ Email format validation failed: Created user with invalid email {email}")
            else:
                print(f"✓ Successfully caught invalid email format: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"✓ Successfully caught invalid email format: {str(e)}")

    # Test Case 5: Invalid AccountId
    try:
        user_data = {
            "accountId": "507f1f77bcf86cd799439011",  # Random non-existent ObjectId
            "username": generate_random_username(),
            "email": generate_random_email(),
            "password": "password123",
            "firstName": "Test",
            "lastName": "User",
            "gender": "male",
            "isAccountOwner": False
        }
        response = requests.post(f"{API_BASE_URL}/user", json=user_data)
        if response.status_code == 200:
            errors.append("✗ Foreign key validation failed: Created user with non-existent accountId")
        else:
            print(f"✓ Successfully caught invalid account ID: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"✓ Successfully caught invalid account ID: {str(e)}")

    return errors

def populate_users(count: int = 50) -> None:
    """Create specified number of valid users via API"""
    # Create a test account for all users
    account_id = create_account()
    
    print(f"\nCreating {count} users...")
    for i in range(count):
        try:
            user_data = {
                "accountId": account_id,
                "username": generate_random_username(),
                "email": generate_random_email(),
                "password": "password123",
                "firstName": f"Test{i}",
                "lastName": "User",
                "gender": "male" if i % 2 == 0 else "female",
                "isAccountOwner": False
            }
            response = requests.post(f"{API_BASE_URL}/user", json=user_data)
            response.raise_for_status()
            user_id = response.json()["_id"]
            created_entities["user"].append(user_id)
            print(f"Created user {i+1}/{count}: {user_id}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to create user {i+1}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Populate database tables with test data')
    parser.add_argument('--table', help='Table to populate (omit for all tables)')
    parser.add_argument('--count', type=int, default=50, help='Number of records to create (default: 50)')
    parser.add_argument('--remove', action='store_true', help='Remove created entities after execution')
    args = parser.parse_args()

    try:
        if args.table:
            # Single table
            if args.table.lower() == "user":
                # Run test cases first
                print("\nRunning User entity test cases...")
                account_id = create_account()
                errors = test_user_creation(account_id)
                
                if errors:
                    print("\nTest cases failed:")
                    for error in errors:
                        print(error)
                    if args.remove:
                        remove_created_entities()
                    return
                
                print("\nAll test cases passed!")
                
                # Populate with valid data
                populate_users(args.count)
            else:
                print(f"Table {args.table} not implemented yet")
        else:
            # All tables (implement other tables here)
            print("\nPopulating all tables...")
            populate_users(args.count)
            
        if args.remove:
            remove_created_entities()
            
    except Exception as e:
        print(f"\nError during execution: {str(e)}")
        if args.remove:
            print("\nRemoving any created entities due to error...")
            remove_created_entities()

if __name__ == "__main__":
    main() 