#!/usr/bin/env python3
"""
Basic API functionality tests.
Tests fundamental GET /user/{id} and GET /user endpoints without additional parameters.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.common_test_framework import CommonTestFramework, TEST_USERS

class BasicAPITester(CommonTestFramework):
    """Test basic API functionality"""
    
    def test_individual_user_gets(self) -> bool:
        """Test GET /user/{id} for various user scenarios"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Valid user with no validation issues
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}", 
            "Get valid user",
            expected_notifications=[],
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: User with enum validation issue
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['bad_enum']}", 
            "Get user with bad enum",
            expected_notifications=["gender"],
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 3: User with currency validation issue
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['bad_currency']}", 
            "Get user with bad currency",
            expected_notifications=["netWorth"],
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 4: User with FK issue (only shows notification when FK validation is ON)
        tests_total += 1
        expected_fk_notifications = ["accountId"] if "FK_ON" in self.mode_name else []
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['bad_fk']}", 
            "Get user with bad FK",
            expected_notifications=expected_fk_notifications,
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 5: User with multiple validation issues
        tests_total += 1
        expected_multi_notifications = ["gender", "netWorth"]
        if "FK_ON" in self.mode_name:
            expected_multi_notifications.append("accountId")
            
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['multiple_errors']}", 
            "Get user with multiple errors",
            expected_notifications=expected_multi_notifications,
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 6: Non-existent user (should return 404)
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user/nonexistent_user_123456", 
            "Get non-existent user",
            expected_status=404,
            should_have_data=False
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Individual user tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_user_list(self) -> bool:
        """Test GET /user basic list functionality"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Basic list request
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user", 
            "Get user list",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: List with pagination parameters
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?pageSize=3", 
            "Get user list with page size",
            should_have_data=True
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 User list tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def run_all_tests(self) -> bool:
        """Run all basic API tests"""
        if self.verbose:
            print(f"\n🧪 BASIC API TESTS - {self.mode_name}")
            print("=" * 60)
        
        # Write curl commands (only for first mode)
        
        # Run tests
        test1_result = self.test_individual_user_gets()
        test2_result = self.test_user_list()
        
        overall_success = test1_result and test2_result
        
        if self.verbose:
            status = "✅ ALL PASS" if overall_success else "❌ SOME FAILED"
            print(f"\n{status} - Basic API Tests ({self.mode_name})")
            
        return overall_success

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Basic API functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                       help='Server URL for API tests')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', action='store_true',
                       help='Write curl commands to curl.sh')
    args = parser.parse_args()
    
    print("🚀 Basic API Functionality Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print("=" * 50)
    
    tester = BasicAPITester(args.config_file, args.server_url, args.verbose, args.curl, "Standalone")
    
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