#!/usr/bin/env python3
"""
Simple API test to debug validation issues
"""

import sys
import json
import requests
import subprocess
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_single_api_call():
    """Test a single API call with known bad data"""
    
    # Test the user with negative networth
    user_id = "68814e0e73b517d9e048b093"
    url = f"http://localhost:5500/api/user/{user_id}"
    
    print(f"🧪 Testing GET {url}")
    print("=" * 60)
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            response_data = response.json()
            print("Response structure:")
            for key, value in response_data.items():
                if key == 'data' and isinstance(value, dict):
                    print(f"  {key}: {{user object with {len(value)} fields}}")
                    # Show just the netWorth field if it exists
                    if 'netWorth' in value:
                        print(f"    netWorth: {value['netWorth']}")
                elif key == 'notifications':
                    if value is None:
                        print(f"  {key}: null")
                    elif isinstance(value, list):
                        print(f"  {key}: [{len(value)} notifications]")
                        for i, notif in enumerate(value):
                            print(f"    {i+1}. {notif.get('type', 'UNKNOWN')}: {notif.get('message', 'no message')}")
                            if 'field_name' in notif:
                                print(f"       Field: {notif['field_name']}")
                    else:
                        print(f"  {key}: {type(value).__name__}")
                else:
                    print(f"  {key}: {type(value).__name__}")
            
            # Check specifically for validation issues
            has_notifications = (
                'notifications' in response_data and 
                response_data['notifications'] is not None and
                len(response_data.get('notifications', [])) > 0
            )
            
            print()
            if has_notifications:
                print("✅ Found notifications in response")
                notifications = response_data['notifications']
                validation_notifications = [n for n in notifications if n.get('type') == 'VALIDATION']
                if validation_notifications:
                    print(f"✅ Found {len(validation_notifications)} validation notifications")
                    for notif in validation_notifications:
                        if notif.get('field_name') == 'netWorth':
                            print("✅ Found netWorth validation error!")
                        elif notif.get('field_name') == 'gender':
                            print("✅ Found gender validation error!")
                else:
                    print("⚠️  No validation notifications found")
            else:
                print("❌ No notifications found in response")
                print("   This indicates the notification system is not working properly")
            
        else:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse response as JSON: {e}")
        print(f"Raw response: {response.text}")

def main():
    print("🧪 SIMPLE API VALIDATION TEST")
    print("=" * 80)
    print("Testing single API call to debug notification system")
    print()
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:5500/api/metadata", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
    except:
        print("❌ Server is not running. Please start it first.")
        print("   Run: ./1.run.sh run mongo")
        return 1
    
    test_single_api_call()
    return 0

if __name__ == "__main__":
    sys.exit(main())