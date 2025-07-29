#!/usr/bin/env python3
"""
Quick API test to debug notification issues
"""

import requests
import json

def test_negative_networth_user():
    """Test API with a user that has negative networth"""
    
    # Replace with actual user ID that has negative networth
    user_id = "68814e148f4cb0743baec721"  # From your earlier example
    url = f"http://localhost:5500/api/user/{user_id}"
    
    print(f"Testing GET {url}")
    print("=" * 60)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse response as JSON: {e}")
        print(f"Raw response: {response.text}")

def test_with_view_param():
    """Test API with view parameter (FK processing)"""
    
    user_id = "68814e148f4cb0743baec721"
    view_param = "%7B%22account%22%3A%5B%22id%22%5D%7D"  # {"account":["id"]}
    url = f"http://localhost:5500/api/user/{user_id}?view={view_param}"
    
    print(f"\nTesting GET {url}")
    print("=" * 60)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print("Response Body:")
        print(json.dumps(response.json(), indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse response as JSON: {e}")
        print(f"Raw response: {response.text}")

if __name__ == "__main__":
    print("🧪 API Debug Test - Field Validation Notifications")
    print("=" * 80)
    
    test_negative_networth_user()
    test_with_view_param()