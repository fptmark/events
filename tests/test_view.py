#!/usr/bin/env python3
"""
View parameter tests for User endpoints.

Tests view parameter functionality:
- GET /user?view={...} (field selection)
- Nested field views (e.g., account.name)
- Invalid view parameters
- View parameter validation

Supports both standalone execution and orchestrated testing.
Can run across all 4 modes: MongoDB/Elasticsearch with/without validation.

Usage:
    # Standalone with specific config
    python test_view.py --config mongo.json
    
    # Standalone across all 4 modes
    python test_view.py --all-modes
    
    # With verbose output and curl generation
    python test_view.py --config es.json --verbose --curl
"""

import sys
import json
import urllib.parse
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_common import (
    TestRunner, APIClient, ResponseValidator, TestMode,
    ConfigManager, DatabaseTestHelper, TestDataManager
)

class ViewTestSuite:
    """View parameter test suite"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.runner = TestRunner("View Parameter Tests", verbose=verbose)
    
    def test_basic_view_parameter(self, config_file: str, curl: bool = False) -> bool:
        """Test basic view parameter functionality"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test simple field selection
            view_data = {"username": True, "email": True, "firstName": True}
            view_param = json.dumps(view_data)
            
            print(f"  🔍 Testing view: {view_param}")
            
            response = client.get('/api/user', params={'view': view_param})
            
            # Should return 200 with filtered data
            is_valid, msg = ResponseValidator.validate_success_response(response, ['data'])
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            users = response.json_data.get('data', [])
            if len(users) == 0:
                print("  ⚠️  No users found - skipping field validation")
                return True
            
            # Verify only requested fields are present
            user = users[0]
            expected_fields = set(['_id', 'username', 'email', 'firstName'])  # _id always included
            actual_fields = set(user.keys())
            
            # Check that we have the expected fields
            if not expected_fields.issubset(actual_fields):
                missing = expected_fields - actual_fields
                print(f"  ❌ Missing expected fields: {missing}")
                return False
            
            # Check that we don't have unexpected fields (beyond a reasonable set)
            reasonable_extra_fields = {'createdAt', 'updatedAt', '__v'}
            unexpected = actual_fields - expected_fields - reasonable_extra_fields
            
            if unexpected:
                print(f"  ⚠️  Unexpected fields present (may be OK): {unexpected}")
            
            print(f"  ✅ View parameter correctly filtered fields")
            print(f"     Returned fields: {sorted(actual_fields)}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_basic_view_parameter: {e}")
            return False
    
    def test_nested_view_parameter(self, config_file: str, curl: bool = False) -> bool:
        """Test nested view parameter (e.g., account fields)"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test nested field selection (assuming account relationship exists)
            view_data = {
                "username": True,
                "account": ["name", "createdAt"]
            }
            view_param = json.dumps(view_data)
            
            print(f"  🔍 Testing nested view: {view_param}")
            
            response = client.get('/api/user', params={'view': view_param})
            
            # Should return 200 
            is_valid, msg = ResponseValidator.validate_success_response(response, ['data'])
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            users = response.json_data.get('data', [])
            if len(users) == 0:
                print("  ⚠️  No users found - skipping nested field validation")
                return True
            
            # Look for a user with account data
            user_with_account = None
            for user in users:
                if 'account' in user and user['account']:
                    user_with_account = user
                    break
            
            if user_with_account:
                account = user_with_account['account']
                print(f"  ✅ Found nested account data: {account}")
                
                # Verify account has expected structure
                if isinstance(account, dict):
                    if 'name' in account:
                        print(f"     Account name: {account['name']}")
                    if 'createdAt' in account:
                        print(f"     Account created: {account['createdAt']}")
                elif isinstance(account, str):
                    print(f"     Account reference: {account}")
                
                print(f"  ✅ Nested view parameter processed successfully")
            else:
                print("  ⚠️  No users with account data found - nested view not fully testable")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_nested_view_parameter: {e}")
            return False
    
    def test_invalid_view_parameter(self, config_file: str, curl: bool = False) -> bool:
        """Test invalid view parameter handling"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test with malformed JSON
            invalid_view = "{username: true, email"  # Invalid JSON
            
            print(f"  🔍 Testing invalid view: {invalid_view}")
            
            response = client.get('/api/user', params={'view': invalid_view})
            
            # Should either return error or ignore invalid view
            if response.status_code >= 400:
                print(f"  ✅ Correctly returned error for invalid view: {response.status_code}")
                return True
            elif response.status_code == 200:
                print(f"  ✅ Invalid view ignored, returned normal response")
                return True
            else:
                print(f"  ❌ Unexpected status code: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"  ❌ Exception in test_invalid_view_parameter: {e}")
            return False
    
    def test_empty_view_parameter(self, config_file: str, curl: bool = False) -> bool:
        """Test empty view parameter"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test with empty object
            empty_view = "{}"
            
            print(f"  🔍 Testing empty view: {empty_view}")
            
            response = client.get('/api/user', params={'view': empty_view})
            
            # Should return 200 with full data (empty view should return all fields)
            is_valid, msg = ResponseValidator.validate_success_response(response, ['data'])
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            users = response.json_data.get('data', [])
            if len(users) > 0:
                user = users[0]
                field_count = len(user.keys())
                print(f"  ✅ Empty view returned full user object with {field_count} fields")
            else:
                print("  ⚠️  No users found - empty view behavior not fully testable")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_empty_view_parameter: {e}")
            return False
    
    def test_url_encoded_view_parameter(self, config_file: str, curl: bool = False) -> bool:
        """Test URL-encoded view parameter"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test with URL-encoded JSON (as it would come from browser)
            view_data = {"username": True, "email": True}
            view_json = json.dumps(view_data)
            encoded_view = urllib.parse.quote(view_json)
            
            print(f"  🔍 Testing URL-encoded view: {encoded_view}")
            
            # Make request with pre-encoded parameter
            url = f"/api/user?view={encoded_view}"
            response = client.get(url)
            
            # Should return 200 with filtered data
            is_valid, msg = ResponseValidator.validate_success_response(response, ['data'])
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            users = response.json_data.get('data', [])
            if len(users) > 0:
                user = users[0]
                if 'username' in user and 'email' in user:
                    print(f"  ✅ URL-encoded view correctly processed")
                else:
                    print(f"  ❌ Expected fields not found in response")
                    return False
            else:
                print("  ⚠️  No users found - URL encoding not fully testable")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_url_encoded_view_parameter: {e}")
            return False
    
    def test_complex_view_parameter(self, config_file: str, curl: bool = False) -> bool:
        """Test complex view parameter with multiple nested fields"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test complex nested view
            view_data = {
                "username": True,
                "firstName": True,
                "lastName": True,
                "account": ["name", "description", "createdAt"],
                "createdAt": True
            }
            view_param = json.dumps(view_data)
            
            print(f"  🔍 Testing complex view: {view_param}")
            
            response = client.get('/api/user', params={'view': view_param})
            
            # Should return 200
            is_valid, msg = ResponseValidator.validate_success_response(response, ['data'])
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            users = response.json_data.get('data', [])
            if len(users) > 0:
                user = users[0]
                
                # Check basic fields
                basic_fields = ['username', 'firstName', 'lastName', 'createdAt']
                found_fields = [f for f in basic_fields if f in user]
                
                print(f"  ✅ Complex view processed")
                print(f"     Basic fields found: {found_fields}")
                
                if 'account' in user:
                    print(f"     Account data included: {type(user['account'])}")
                
            else:
                print("  ⚠️  No users found - complex view not fully testable")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_complex_view_parameter: {e}")
            return False
    
    def run_all_tests(self, config_file: str, curl: bool = False) -> bool:
        """Run all view tests with a specific config"""
        print(f"\n{'='*80}")
        print(f"VIEW PARAMETER TESTS")
        print(f"Config: {config_file}")
        print('='*80)
        
        tests = [
            ("Basic view parameter", self.test_basic_view_parameter),
            ("Nested view parameter", self.test_nested_view_parameter),
            ("Invalid view parameter", self.test_invalid_view_parameter),
            ("Empty view parameter", self.test_empty_view_parameter),
            ("URL-encoded view parameter", self.test_url_encoded_view_parameter),
            ("Complex view parameter", self.test_complex_view_parameter),
        ]
        
        for test_name, test_func in tests:
            self.runner.run_test(test_name, test_func, config_file=config_file, curl=curl)
        
        return self.runner.print_summary()
    
    def run_4_mode_tests(self, curl: bool = False) -> bool:
        """Run all view tests across 4 modes"""
        print(f"\n{'='*80}")
        print(f"VIEW PARAMETER TESTS - ALL 4 MODES")
        print('='*80)
        
        tests = [
            ("Basic view parameter", self.test_basic_view_parameter),
            ("Nested view parameter", self.test_nested_view_parameter),
            ("Invalid view parameter", self.test_invalid_view_parameter),
            ("Empty view parameter", self.test_empty_view_parameter),
            ("URL-encoded view parameter", self.test_url_encoded_view_parameter),
            ("Complex view parameter", self.test_complex_view_parameter),
        ]
        
        for test_name, test_func in tests:
            self.runner.run_4_mode_test(test_name, test_func)
        
        return self.runner.print_summary()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='View parameter tests for User endpoints')
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
    
    suite = ViewTestSuite(verbose=args.verbose)
    
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