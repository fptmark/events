#!/usr/bin/env python3
"""
Debug Elasticsearch ID handling
"""
import requests
import json

def debug_es_ids():
    base_url = "http://localhost:5500"
    
    print("🔍 Debugging Elasticsearch ID handling...")
    
    # Get user list to see actual IDs
    print("\n1. Getting user list to see IDs...")
    response = requests.get(f"{base_url}/api/user?pageSize=3")
    if response.status_code == 200:
        data = response.json()
        users = data.get('data', [])
        print(f"   ✅ Got {len(users)} users")
        
        for i, user in enumerate(users[:3]):
            user_id = user.get('id')
            print(f"   User {i+1}: id='{user_id}' (type: {type(user_id)})")
            
            # Try to fetch this user by ID
            print(f"     Trying to fetch user by ID: {user_id}")
            detail_response = requests.get(f"{base_url}/api/user/{user_id}")
            print(f"     Response: {detail_response.status_code}")
            if detail_response.status_code != 200:
                print(f"     Error: {detail_response.text}")
            else:
                detail_data = detail_response.json()
                retrieved_id = detail_data.get('id')
                print(f"     Retrieved ID: '{retrieved_id}'")
                print(f"     Match: {retrieved_id == user_id}")
            print()
            
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    try:
        debug_es_ids()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on http://localhost:5500?")
    except Exception as e:
        print(f"❌ Error: {e}")