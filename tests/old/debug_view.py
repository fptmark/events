#!/usr/bin/env python3
"""
Quick debug script to test view parameter functionality
"""
import requests
import urllib.parse
import json

def test_view_parameter():
    base_url = "http://localhost:5500"
    
    print("🔍 Testing view parameter functionality...")
    
    # Test 1: Basic user list without view
    print("\n1. Testing basic user list...")
    response = requests.get(f"{base_url}/api/user?pageSize=3")
    if response.status_code == 200:
        data = response.json()
        users = data.get('data', [])
        print(f"   ✅ Got {len(users)} users")
        if users:
            user = users[0]
            print(f"   Sample user: id={user.get('id')}, username={user.get('username')}, accountId={user.get('accountId')}")
        else:
            print("   ⚠️  No users found - can't test FK relationships")
            return
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")
        return
    
    # Test 2: User list with view parameter
    print("\n2. Testing user list with view parameter...")
    view_spec = '{"account":["createdAt"]}'
    encoded_view = urllib.parse.quote(view_spec)
    
    response = requests.get(f"{base_url}/api/user?view={encoded_view}&pageSize=3")
    if response.status_code == 200:
        data = response.json()
        users = data.get('data', [])
        print(f"   ✅ Got {len(users)} users with view parameter")
        
        for i, user in enumerate(users):
            print(f"   User {i+1}:")
            print(f"     - id: {user.get('id')}")
            print(f"     - username: {user.get('username')}")
            print(f"     - accountId: {user.get('accountId')}")
            
            account_data = user.get('account')
            if account_data:
                print(f"     - account: {account_data}")
                if account_data.get('exists'):
                    print("       ✅ Account exists flag = True")
                    if 'createdAt' in account_data:
                        print(f"       ✅ Account createdAt = {account_data['createdAt']}")
                    else:
                        print("       ❌ Missing createdAt field")
                else:
                    print(f"       ⚠️  Account exists flag = {account_data.get('exists')}")
            else:
                if user.get('accountId'):
                    print("       ❌ No account data despite having accountId")
                else:
                    print("       ℹ️  No accountId, so no account data expected")
            print()
            
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")
    
    # Test 3: Check if we can get account data directly
    print("\n3. Testing direct account access...")
    response = requests.get(f"{base_url}/api/account?pageSize=3")
    if response.status_code == 200:
        data = response.json()
        accounts = data.get('data', [])
        print(f"   ✅ Got {len(accounts)} accounts")
        if accounts:
            account = accounts[0]
            print(f"   Sample account: id={account.get('id')}, createdAt={account.get('createdAt')}")
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    try:
        test_view_parameter()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on http://localhost:5500?")
    except Exception as e:
        print(f"❌ Error: {e}")