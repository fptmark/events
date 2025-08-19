#!/usr/bin/env python3
"""
Test unique constraint violations for both MongoDB and Elasticsearch
"""

import requests
import json
import time
import sys

def test_unique_violations(base_url="http://localhost:5500"):
    """Test unique constraint violations"""
    
    print("🧪 Testing Unique Constraint Violations")
    print("=" * 50)
    
    # Get an existing account to use for testing
    print("📝 Setup: Getting existing account...")
    account_response = requests.get(f"{base_url}/api/account")
    if account_response.status_code == 200:
        accounts = account_response.json().get("data", [])
        if accounts:
            account_id = accounts[0]["id"]
            print(f"   ✅ Using existing account: {account_id}")
        else:
            print("   ❌ No accounts found")
            return False
    else:
        print("   ❌ Failed to get accounts")
        return False
    
    # Test data with unique fields
    user_data = {
        "username": f"test_unique_user_{int(time.time())}",
        "email": f"test_unique_{int(time.time())}@example.com", 
        "password": "password123",
        "firstName": "Test",
        "lastName": "User",
        "gender": "male",
        "isAccountOwner": True,
        "netWorth": 50000,
        "accountId": account_id
    }
    
    # Test 1: Create first user (should succeed)
    print("📝 Test 1: Creating first user...")
    response1 = requests.post(f"{base_url}/api/user", json=user_data)
    print(f"   Status: {response1.status_code}")
    
    if response1.status_code in [200, 201]:
        print("   ✅ First user created successfully")
        user_id = response1.json().get("data", {}).get("id")
        print(f"   User ID: {user_id}")
    else:
        print("   ❌ Failed to create first user")
        print(f"   Response: {response1.text}")
        return False
    
    # Test 2: Try to create user with same username (should fail)
    print("\\n📝 Test 2: Creating user with duplicate username...")
    duplicate_username_data = user_data.copy()
    duplicate_username_data["email"] = f"different_email_{int(time.time())}@example.com"
    
    response2 = requests.post(f"{base_url}/api/user", json=duplicate_username_data)
    print(f"   Status: {response2.status_code}")
    
    if response2.status_code in [409, 422]:  # Conflict or Unprocessable Entity
        print("   ✅ Duplicate username correctly rejected")
        response_data = response2.json()
        print(f"   Error type: {response_data.get('notifications', {}).get('errors', [{}])[0].get('type', 'unknown')}")
    else:
        print("   ❌ Duplicate username should have been rejected")
        print(f"   Response: {response2.text}")
    
    # Test 3: Try to create user with same email (should fail)  
    print("\\n📝 Test 3: Creating user with duplicate email...")
    duplicate_email_data = user_data.copy()
    duplicate_email_data["username"] = f"different_username_{int(time.time())}"
    
    response3 = requests.post(f"{base_url}/api/user", json=duplicate_email_data)
    print(f"   Status: {response3.status_code}")
    
    if response3.status_code in [409, 422]:  # Conflict or Unprocessable Entity
        print("   ✅ Duplicate email correctly rejected")
        response_data = response3.json()
        print(f"   Error type: {response_data.get('notifications', {}).get('errors', [{}])[0].get('type', 'unknown')}")
    else:
        print("   ❌ Duplicate email should have been rejected")
        print(f"   Response: {response3.text}")
    
    # Test 4: Create user with different username AND email (should succeed)
    print("\\n📝 Test 4: Creating user with unique username and email...")
    unique_data = {
        "username": f"unique_user_{int(time.time())}",
        "email": f"unique_{int(time.time())}@example.com",
        "password": "password123", 
        "firstName": "Unique",
        "lastName": "User",
        "gender": "female",
        "isAccountOwner": False,
        "netWorth": 75000,
        "accountId": account_id
    }
    
    response4 = requests.post(f"{base_url}/api/user", json=unique_data)
    print(f"   Status: {response4.status_code}")
    
    if response4.status_code in [200, 201]:
        print("   ✅ Unique user created successfully")
        user_id2 = response4.json().get("data", {}).get("id")
        print(f"   User ID: {user_id2}")
    else:
        print("   ❌ Unique user creation failed")
        print(f"   Response: {response4.text}")
    
    print("\\n" + "=" * 50)
    print("🧪 Unique Constraint Tests Complete")
    
    return True

if __name__ == "__main__":
    test_unique_violations()