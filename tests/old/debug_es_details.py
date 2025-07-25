#!/usr/bin/env python3
"""
Debug Elasticsearch response details
"""
import requests
import json

def debug_es_response():
    base_url = "http://localhost:5500"
    
    print("🔍 Debugging Elasticsearch response details...")
    
    # Get user list to see actual IDs
    print("\n1. Getting user list...")
    response = requests.get(f"{base_url}/api/user?pageSize=1")
    if response.status_code == 200:
        data = response.json()
        users = data.get('data', [])
        if users:
            user = users[0]
            user_id = user.get('id')
            print(f"   First user from list:")
            print(f"   ID: '{user_id}'")
            print(f"   Full user: {json.dumps(user, indent=2)[:500]}...")
            
            # Try to fetch this user by ID
            print(f"\n2. Fetching user by ID: {user_id}")
            detail_response = requests.get(f"{base_url}/api/user/{user_id}")
            print(f"   Response status: {detail_response.status_code}")
            
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                print(f"   Response data: {json.dumps(detail_data, indent=2)[:500]}...")
            else:
                print(f"   Error response: {detail_response.text}")
                
    else:
        print(f"   ❌ Failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    try:
        debug_es_response()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on http://localhost:5500?")
    except Exception as e:
        print(f"❌ Error: {e}")