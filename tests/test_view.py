#!/usr/bin/env python3
"""
View parameter tests.
Tests API endpoints with view parameters to verify FK sub-object population.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.common_test_framework import CommonTestFramework, TEST_USERS, TEST_ACCOUNTS

class ViewParameterTester(CommonTestFramework):
    """Test view parameter functionality"""
    
    def test_individual_user_with_view(self) -> bool:
        """Test GET /user/{id} with view parameters"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Valid FK user with account view
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", 
            "Get valid user with account ID view",
            expected_notifications=[],
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: Valid FK user with full account view
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", 
            "Get valid user with full account view",
            expected_notifications=[],
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 3: User with bad FK and account view (should show FK validation notification)
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['bad_fk']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", 
            "Get user with bad FK and account view",
            expected_notifications=["accountId"],  # FK validation always triggers with view
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 4: User with multiple errors and account view
        tests_total += 1
        expected_notifications = ["gender", "netWorth", "accountId"]  # FK validation always triggers with view
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['multiple_errors']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", 
            "Get user with multiple errors and account view",
            expected_notifications=expected_notifications,
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 5: Valid user with invalid view field (should still work, just ignore bad fields)
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D", 
            "Get valid user with invalid view field",
            expected_notifications=[],
            should_have_data=True
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Individual user view tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_user_list_with_view(self) -> bool:
        """Test GET /user list with view parameters"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: User list with account ID view
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D", 
            "Get user list with account ID view",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: User list with full account view
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", 
            "Get user list with full account view",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 3: User list with pagination and view
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D", 
            "Get user list with pagination and view",
            should_have_data=True
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 User list view tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def run_all_tests(self) -> bool:
        """Run all view parameter tests"""
        if self.verbose:
            print(f"\n🧪 VIEW PARAMETER TESTS - {self.mode_name}")
            print("=" * 60)
        
        # Pre-write all curl commands for this test suite
        test_urls = [
            # Individual user view tests
            ("GET", f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get valid user with account ID view"),
            ("GET", f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", "Get valid user with full account view"),
            ("GET", f"/api/user/{TEST_USERS['bad_fk']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user with bad FK and account view"),
            ("GET", f"/api/user/{TEST_USERS['multiple_errors']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user with multiple errors and account view"),
            ("GET", f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D", "Get valid user with invalid view field"),
            # User list view tests
            ("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user list with account ID view"),
            ("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", "Get user list with full account view"),
            ("GET", "/api/user?pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user list with pagination and view"),
        ]
        self.write_curl_commands_for_test_suite("View Parameter Tests", test_urls)
        
        # Run tests
        test1_result = self.test_individual_user_with_view()
        test2_result = self.test_user_list_with_view()
        
        overall_success = test1_result and test2_result
        
        if self.verbose:
            status = "✅ ALL PASS" if overall_success else "❌ SOME FAILED"
            print(f"\n{status} - View Parameter Tests ({self.mode_name})")
            
        return overall_success

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='View parameter functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                       help='Server URL for API tests')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', action='store_true',
                       help='Write curl commands to curl.sh')
    args = parser.parse_args()
    
    print("🚀 View Parameter Functionality Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print("=" * 50)
    
    tester = ViewParameterTester(args.config_file, args.server_url, args.verbose, args.curl, "Standalone")
    
    # Setup database connection
    if not await tester.setup_database_connection():
        print("❌ Failed to setup database connection")
        return False
    
    try:
        success = tester.run_all_tests()
        
        # Print final result
        print(f"\n📊 FINAL RESULT: {'✅ PASS' if success else '❌ FAIL'}")
        return success
        
    finally:
        await tester.cleanup_database_connection()

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTests failed with exception: {e}")
        sys.exit(1)