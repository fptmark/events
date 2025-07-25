#!/usr/bin/env python3
"""
FK Processing Test Suite

Tests all 4 conditions for FK processing:
1. get_validation=get_all, no view param -> should have data
2. get_validation=get_all, with view param -> should have data  
3. get_validation=off, no view param -> should have data
4. get_validation=off, with view param -> should have data

Usage:
    python test_fk_processing.py config.json
"""

import sys
import asyncio
import json
from urllib.parse import quote
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import BaseTestFramework

class FKProcessingTester(BaseTestFramework):
    """FK processing test suite"""
    
    def __init__(self, config_file: str, server_url: str = "http://127.0.0.1:5500", verbose: bool = False, curl: bool = False):
        super().__init__(config_file, server_url, verbose, curl)
        self.test_user_ids = []
        
    def test_get_all_users_no_view(self):
        """Test GET /api/user (no view parameter)"""
        print("🔍 Testing GET /api/user (no view parameter)...")
        
        success, response = self.make_api_request("GET", "/api/user", expected_status=200)
        
        if success:
            data = response.get("data", [])
            print(f"    ✅ Retrieved {len(data)} users")
            return len(data) > 0  # Should have some data
        else:
            print(f"    ❌ Failed to get users: {response}")
            return False
    
    def test_get_all_users_with_view(self):
        """Test GET /api/user?view={"account":["createdAt"]} (with view parameter)"""
        print("🔍 Testing GET /api/user with view parameter...")
        
        # Create view specification
        view_spec = {"account": ["createdAt"]}
        view_param = quote(json.dumps(view_spec))
        url = f"/api/user?view={view_param}"
        
        success, response = self.make_api_request("GET", url, expected_status=200)
        
        if success:
            data = response.get("data", [])
            print(f"    ✅ Retrieved {len(data)} users with view parameter")
            
            # Check if any users have FK data
            fk_data_found = False
            for user in data[:3]:  # Check first 3 users
                if "account" in user:
                    fk_data_found = True
                    account_data = user["account"]
                    print(f"    ✅ Found FK data for user {user.get('id', 'unknown')}: account={account_data}")
                    break
            
            if not fk_data_found:
                print(f"    ⚠️  No FK data found in response (this may be expected)")
                
            return len(data) > 0  # Should have some data
        else:
            print(f"    ❌ Failed to get users with view: {response}")
            return False
    
    def test_get_single_user_no_view(self):
        """Test GET /api/user/{id} (no view parameter)"""
        print("🔍 Testing GET /api/user/{id} (no view parameter)...")
        
        # First get a user ID
        success, response = self.make_api_request("GET", "/api/user", expected_status=200)
        if not success or not response.get("data"):
            print("    ❌ Could not get user list to find user ID")
            return False
            
        users = response.get("data", [])
        if not users:
            print("    ❌ No users found in database")
            return False
            
        user_id = users[0].get("id")
        if not user_id:
            print("    ❌ Could not extract user ID")
            return False
            
        # Test individual user GET
        success, response = self.make_api_request("GET", f"/api/user/{user_id}", expected_status=200)
        
        if success:
            user = response.get("data", {})
            username = user.get("username", "unknown")
            print(f"    ✅ Retrieved individual user: {username}")
            return True
        else:
            print(f"    ❌ Failed to get individual user: {response}")
            return False
    
    def test_get_single_user_with_view(self):
        """Test GET /api/user/{id}?view={"account":["createdAt"]} (with view parameter)"""
        print("🔍 Testing GET /api/user/{id} with view parameter...")
        
        # First get a user ID
        success, response = self.make_api_request("GET", "/api/user", expected_status=200)
        if not success or not response.get("data"):
            print("    ❌ Could not get user list to find user ID")
            return False
            
        users = response.get("data", [])
        if not users:
            print("    ❌ No users found in database")
            return False
            
        user_id = users[0].get("id")
        if not user_id:
            print("    ❌ Could not extract user ID")
            return False
            
        # Create view specification
        view_spec = {"account": ["createdAt"]}
        view_param = quote(json.dumps(view_spec))
        url = f"/api/user/{user_id}?view={view_param}"
        
        # Test individual user GET with view
        success, response = self.make_api_request("GET", url, expected_status=200)
        
        if success:
            user = response.get("data", {})
            username = user.get("username", "unknown")
            print(f"    ✅ Retrieved individual user with view: {username}")
            
            # Check if FK data is present
            if "account" in user:
                account_data = user["account"]
                print(f"    ✅ Found FK data: account={account_data}")
            else:
                print(f"    ⚠️  No FK data found (this may be expected)")
                
            return True
        else:
            print(f"    ❌ Failed to get individual user with view: {response}")
            return False
    
    def check_current_validation_setting(self):
        """Check current get_validation setting"""
        print("🔍 Checking current validation setting...")
        
        # Read the config file to see current setting
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            get_validation = config.get("get_validation", "")
            print(f"    Current get_validation: '{get_validation}'")
            
            if get_validation == "get_all":
                print(f"    📋 Testing with validation ENABLED (get_all)")
                return "get_all"
            elif get_validation == "get":
                print(f"    📋 Testing with validation PARTIAL (get only)")
                return "get"
            else:
                print(f"    📋 Testing with validation DISABLED")
                return "off"
                
        except Exception as e:
            print(f"    ❌ Failed to read config: {e}")
            return "unknown"
    
    def run_fk_processing_tests(self):
        """Run all FK processing tests"""
        print("\n" + "="*80)
        print("FK PROCESSING TEST SUITE")
        print("="*80)
        
        # Check validation setting
        validation_setting = self.check_current_validation_setting()
        
        print(f"\nTesting all 4 conditions with validation={validation_setting}:")
        print("1. GET /api/user (no view param)")
        print("2. GET /api/user?view=... (with view param)")
        print("3. GET /api/user/{id} (no view param)")
        print("4. GET /api/user/{id}?view=... (with view param)")
        print()
        
        # Run all tests
        test1 = self.test_get_all_users_no_view()
        test2 = self.test_get_all_users_with_view()
        test3 = self.test_get_single_user_no_view()
        test4 = self.test_get_single_user_with_view()
        
        # Record results
        self.test("GET all users (no view)", lambda: test1, True)
        self.test("GET all users (with view)", lambda: test2, True)
        self.test("GET single user (no view)", lambda: test3, True)
        self.test("GET single user (with view)", lambda: test4, True)
        
        return test1 and test2 and test3 and test4

async def main():
    """Run FK processing tests"""
    parser = BaseTestFramework.create_argument_parser()
    args = parser.parse_args()
    
    print("🚀 Starting FK Processing Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print("="*60)
    
    tester = FKProcessingTester(args.config_file, args.server_url, args.verbose, args.curl)
    
    try:
        # Run FK processing tests
        success = tester.run_fk_processing_tests()
        
        # Print summary
        overall_success = tester.summary()
        
        return overall_success
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    print("FK Processing Test Suite")
    print("Usage: python test_fk_processing.py [config_file]")
    print("Example: python test_fk_processing.py mongo.json")
    print()
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        sys.exit(1)