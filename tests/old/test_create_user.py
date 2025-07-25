#!/usr/bin/env python3
"""
Test user creation to debug the 'Field required' error
"""
import requests
import json
import time

def test_user_creation():
    base_url = "http://localhost:5500"
    
    print("🔍 Testing user creation...")
    
    # Test data that should be valid
    timestamp = int(time.time())
    user_data = {
        "username": f"test_user_{timestamp}",
        "email": f"test_{timestamp}@example.com",
        "password": "password123",
        "firstName": "Test",
        "lastName": "User",
        "gender": "male",
        "isAccountOwner": True,
        "accountId": "507f1f77bcf86cd799439011"
    }
    
    print("📤 Sending user creation request...")
    print(f"Data: {json.dumps(user_data, indent=2)}")
    
    try:
        response = requests.post(f"{base_url}/api/user", json=user_data)
        print(f"📥 Response: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.text:
            try:
                response_data = response.json()
                print(f"Response data: {json.dumps(response_data, indent=2)}")
            except:
                print(f"Raw response: {response.text}")
        
        # Also test the metadata endpoint to see what fields are expected
        print("\n🔍 Checking user metadata...")
        meta_response = requests.get(f"{base_url}/api/metadata")
        if meta_response.status_code == 200:
            metadata = meta_response.json()
            user_metadata = metadata.get('entities', {}).get('User', {})
            if user_metadata:
                print("User field requirements:")
                fields = user_metadata.get('fields', {})
                for field_name, field_info in fields.items():
                    required = field_info.get('required', False)
                    field_type = field_info.get('type', 'Unknown')
                    print(f"  - {field_name}: {field_type} {'(required)' if required else '(optional)'}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on http://localhost:5500?")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_user_creation()