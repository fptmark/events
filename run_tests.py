#!/usr/bin/env python3
"""
Run the specific failing tests to verify fixes
"""

import sys
import json
import requests
from pathlib import Path

# Add project root to path  
sys.path.insert(0, str(Path(__file__).parent))

SERVER_URL = "http://127.0.0.1:5500"
TEST_USER_ID = None  # Will be set dynamically

def create_test_user():
    """Create a test user and return its ID"""
    print("=== Creating Test User ===")
    
    base_url = f"{SERVER_URL}/api/user"
    create_data = {
        "username": "testapi_run",
        "email": "testapi_run@example.com",
        "password": "password123", 
        "firstName": "API",
        "lastName": "Test",
        "gender": "female",
        "netWorth": "$25,750.50",
        "isAccountOwner": True,
        "accountId": "507f1f77bcf86cd799439011"
    }
    
    try:
        response = requests.post(base_url, json=create_data, timeout=10)
        if response.status_code == 200:
            data = response.json()
            user_data = data.get("data", {})
            user_id = user_data.get("id") or user_data.get("_id")
            
            if user_id:
                print(f"✅ Created test user with ID: {user_id}")
                return user_id
            else:
                # Try to find by username if no ID returned
                username = user_data.get("username")
                if username:
                    print(f"🔍 No ID returned, searching for user: {username}")
                    list_response = requests.get(f"{SERVER_URL}/api/user", timeout=10)
                    if list_response.status_code == 200:
                        list_data = list_response.json()
                        users = list_data.get("data", [])
                        for user in users:
                            if user.get("username") == username:
                                found_id = user.get("id") or user.get("_id")
                                if found_id:
                                    print(f"✅ Found user ID via search: {found_id}")
                                    return found_id
                print(f"❌ Could not determine user ID")
                return None
        else:
            print(f"❌ Failed to create test user: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception creating test user: {e}")
        return None

def test_put_endpoint():
    """Test PUT endpoint (Test 4 fix)"""
    print("=== Testing PUT Endpoint Fix ===")
    
    if not TEST_USER_ID:
        print("❌ No TEST_USER_ID available")
        return False
    
    base_url = f"{SERVER_URL}/api/user/{TEST_USER_ID}"
    update_data = {
        "username": "testupdated",
        "email": "updated@example.com",
        "password": "password123",
        "firstName": "Updated", 
        "lastName": "User",
        "gender": "other",
        "netWorth": "$50,000.00",  # Valid currency string
        "isAccountOwner": True,
        "accountId": "507f1f77bcf86cd799439011"
    }
    
    try:
        response = requests.put(base_url, json=update_data, timeout=10)
        print(f"PUT Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"PUT Response: {json.dumps(data, indent=2)}")
            
            user_data = data.get("data")
            if user_data and isinstance(user_data, dict):
                net_worth = user_data.get("netWorth")
                print(f"✅ PUT Success: netWorth stored as {net_worth} (type: {type(net_worth)})")
                return True
            else:
                print(f"❌ PUT Response data is None or invalid: {user_data}")
                return False
        else:
            print(f"❌ PUT Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ PUT Exception: {e}")
        return False

def test_validation_constraints():
    """Test validation constraints (Test 5 fix)"""
    print("\n=== Testing Validation Constraints Fix ===")
    
    if not TEST_USER_ID:
        print("❌ No TEST_USER_ID available")
        return False
    
    base_url = f"{SERVER_URL}/api/user/{TEST_USER_ID}"
    
    # Test invalid range - should be rejected
    invalid_data = {
        "username": "testinvalid",
        "email": "invalid@example.com",
        "password": "password123",
        "firstName": "Invalid",
        "lastName": "Test", 
        "gender": "male",
        "netWorth": "$50,000,000.00",  # 50M > 10M limit
        "isAccountOwner": True,
        "accountId": "507f1f77bcf86cd799439011"
    }
    
    try:
        response = requests.put(base_url, json=invalid_data, timeout=10)
        print(f"Validation test response status: {response.status_code}")
        
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code == 422:  # Validation error
            print(f"✅ Range validation working: correctly rejected high value")
            return True
        elif response.status_code == 200:
            # Check if validation failed (data=null means validation error)
            user_data = response_data.get("data")
            message = response_data.get("message", "")
            level = response_data.get("level", "")
            
            if user_data is None and level == "error" and "validation error" in message.lower():
                print(f"✅ Range validation working: correctly rejected high value via error response")
                return True
            elif user_data is not None:
                stored_value = user_data.get("netWorth")
                print(f"❌ Range validation failed: high value was stored as {stored_value}")
                return False
            else:
                print(f"❌ Unexpected 200 response structure: data={user_data}, level={level}")
                return False
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Validation test exception: {e}")
        return False

def main():
    global TEST_USER_ID
    print("🧪 Testing Fixes for Test 4 & 5")
    print("="*50)
    
    # Create test user first
    TEST_USER_ID = create_test_user()
    if not TEST_USER_ID:
        print("💥 Failed to create test user - cannot proceed")
        return False
    
    # Test 4 fix
    put_success = test_put_endpoint()
    
    # Test 5 fix  
    validation_success = test_validation_constraints()
    
    print(f"\n{'='*50}")
    print("RESULTS:")
    print(f"PUT Test: {'✅ PASS' if put_success else '❌ FAIL'}")
    print(f"Validation Test: {'✅ PASS' if validation_success else '❌ FAIL'}")
    
    if put_success and validation_success:
        print("🎉 Both fixes are working!")
        return True
    else:
        print("💥 Some fixes still need work")
        return False

if __name__ == "__main__":
    main()