#!/usr/bin/env python3
"""
Basic API tests for User endpoints.

Tests fundamental GET operations:
- GET /user (list all users)
- GET /user/{id} (get specific user)

Supports both standalone execution and orchestrated testing.
Can run across all 4 modes: MongoDB/Elasticsearch with/without validation.

Usage:
    # Standalone with specific config
    python test_basic.py --config mongo.json
    
    # Standalone across all 4 modes
    python test_basic.py --all-modes
    
    # With verbose output and curl generation
    python test_basic.py --config es.json --verbose --curl
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_common import (
    TestRunner, APIClient, ResponseValidator, TestMode, 
    ConfigManager, DatabaseTestHelper, TestDataManager
)

class BasicTestSuite:
    """Basic API test suite"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.runner = TestRunner("Basic API Tests", verbose=verbose)
    
    def test_get_user_list(self, config_file: str, curl: bool = False) -> bool:
        """Test GET /user endpoint"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            response = client.get('/api/user')
            
            # Should return 200 with user list
            is_valid, msg = ResponseValidator.validate_success_response(response, ['data'])
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            users = response.json_data.get('data', [])
            print(f"  ✅ Retrieved {len(users)} users")
            
            # Basic structure validation
            if len(users) > 0:
                user = users[0]
                expected_fields = ['_id', 'username', 'email', 'firstName', 'lastName']
                for field in expected_fields:
                    if field not in user:
                        print(f"  ❌ Missing field in user object: {field}")
                        return False
                
                print(f"  ✅ User objects have expected structure")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in get_user_list: {e}")
            return False
    
    def test_get_user_by_id(self, config_file: str, curl: bool = False) -> bool:
        """Test GET /user/{id} endpoint"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # First get a user ID from the list
            list_response = client.get('/api/user')
            if list_response.status_code != 200 or not list_response.json_data:
                print("  ❌ Could not get user list to find test ID")
                return False
            
            users = list_response.json_data.get('data', [])
            if len(users) == 0:
                print("  ⚠️  No users found in database - skipping get by ID test")
                return True  # Not a failure, just no data
            
            # Test with first user
            test_user = users[0]
            user_id = test_user['_id']
            
            print(f"  🔍 Testing with user ID: {user_id}")
            
            response = client.get(f'/api/user/{user_id}')
            
            # Should return 200 with single user
            is_valid, msg = ResponseValidator.validate_success_response(response)
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            user_data = response.json_data
            
            # Verify it's the same user
            if user_data.get('_id') != user_id:
                print(f"  ❌ Returned user ID {user_data.get('_id')} doesn't match requested {user_id}")
                return False
            
            # Verify expected fields
            expected_fields = ['_id', 'username', 'email', 'firstName', 'lastName']
            for field in expected_fields:
                if field not in user_data:
                    print(f"  ❌ Missing field in user object: {field}")
                    return False
            
            print(f"  ✅ Successfully retrieved user: {user_data.get('username')}")
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in get_user_by_id: {e}")
            return False
    
    def test_get_user_by_invalid_id(self, config_file: str, curl: bool = False) -> bool:
        """Test GET /user/{id} with invalid ID"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test with clearly invalid ID
            invalid_id = "nonexistent_user_id_12345"
            
            print(f"  🔍 Testing with invalid user ID: {invalid_id}")
            
            response = client.get(f'/api/user/{invalid_id}')
            
            # Should return 404 
            if response.status_code != 404:
                print(f"  ❌ Expected 404 for invalid ID, got {response.status_code}")
                return False
            
            print(f"  ✅ Correctly returned 404 for invalid user ID")
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in get_user_by_invalid_id: {e}")
            return False
    
    def test_get_user_empty_id(self, config_file: str, curl: bool = False) -> bool:
        """Test GET /user/ (empty ID - should route to list)"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test with trailing slash (should route to list endpoint)
            response = client.get('/api/user/')
            
            # Should behave same as GET /user
            is_valid, msg = ResponseValidator.validate_success_response(response, ['data'])
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            users = response.json_data.get('data', [])
            print(f"  ✅ GET /user/ correctly routed to list endpoint, got {len(users)} users")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in get_user_empty_id: {e}")
            return False
    
    def test_basic_connectivity(self, config_file: str, curl: bool = False) -> bool:
        """Test basic server connectivity"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test metadata endpoint as connectivity check
            response = client.get('/api/metadata')
            
            if response.status_code != 200:
                print(f"  ❌ Metadata endpoint failed: {response.status_code}")
                return False
            
            print(f"  ✅ Server connectivity confirmed")
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in basic_connectivity: {e}")
            return False
    
    def run_all_tests(self, config_file: str, curl: bool = False) -> bool:
        """Run all basic tests with a specific config"""
        print(f"\n{'='*80}")
        print(f"BASIC API TESTS")
        print(f"Config: {config_file}")
        print('='*80)
        
        tests = [
            ("Basic Connectivity", self.test_basic_connectivity),
            ("GET /user (list all)", self.test_get_user_list),
            ("GET /user/{id} (valid ID)", self.test_get_user_by_id),
            ("GET /user/{id} (invalid ID)", self.test_get_user_by_invalid_id),
            ("GET /user/ (empty ID routing)", self.test_get_user_empty_id),
        ]
        
        for test_name, test_func in tests:
            self.runner.run_test(test_name, test_func, config_file=config_file, curl=curl)
        
        return self.runner.print_summary()
    
    def run_4_mode_tests(self, curl: bool = False) -> bool:
        """Run all basic tests across 4 modes"""
        print(f"\n{'='*80}")
        print(f"BASIC API TESTS - ALL 4 MODES")
        print('='*80)
        
        tests = [
            ("Basic Connectivity", self.test_basic_connectivity),
            ("GET /user (list all)", self.test_get_user_list),
            ("GET /user/{id} (valid ID)", self.test_get_user_by_id),
            ("GET /user/{id} (invalid ID)", self.test_get_user_by_invalid_id),
            ("GET /user/ (empty ID routing)", self.test_get_user_empty_id),
        ]
        
        for test_name, test_func in tests:
            self.runner.run_4_mode_test(test_name, test_func)
        
        return self.runner.print_summary()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Basic API tests for User endpoints')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--all-modes', action='store_true', 
                       help='Run tests across all 4 modes (MongoDB/ES with/without validation)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--curl', action='store_true', help='Generate curl.sh file')
    
    args = parser.parse_args()
    
    if not args.config and not args.all_modes:
        print("❌ Must specify either --config <file> or --all-modes")
        return 1
    
    if args.config and args.all_modes:
        print("❌ Cannot specify both --config and --all-modes")
        return 1
    
    suite = BasicTestSuite(verbose=args.verbose)
    
    try:
        if args.all_modes:
            success = suite.run_4_mode_tests(curl=args.curl)
        else:
            success = suite.run_all_tests(args.config, curl=args.curl)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())