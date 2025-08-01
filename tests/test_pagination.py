#!/usr/bin/env python3
"""
Pagination tests.
Tests API endpoints with pagination parameters to verify proper page handling.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.common_test_framework import CommonTestFramework, TEST_USERS, TEST_ACCOUNTS

class PaginationTester(CommonTestFramework):
    """Test pagination functionality"""
    
    def test_basic_pagination(self) -> bool:
        """Test basic pagination parameters"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Default pagination (no parameters)
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user", 
            "Get user list with default pagination",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: Custom page size
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?pageSize=3", 
            "Get user list with page size 3",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 3: Specific page
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?page=1&pageSize=5", 
            "Get user list page 1 with size 5",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 4: Second page
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?page=2&pageSize=3", 
            "Get user list page 2 with size 3",
            should_have_data=False  # May be empty if not enough users
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Basic pagination tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_pagination_edge_cases(self) -> bool:
        """Test pagination edge cases"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Page 0 (should default to page 1)
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?page=0&pageSize=5", 
            "Get user list with page 0",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: Very large page size
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?pageSize=1000", 
            "Get user list with large page size",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 3: Page beyond available data
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?page=999&pageSize=5", 
            "Get user list beyond available pages",
            should_have_data=False  # Should be empty
        ):
            tests_passed += 1
            
        # Test 4: Invalid page size (should handle gracefully)
        tests_total += 1
        if self.test_api_call(
            "GET", 
            "/api/user?pageSize=0", 
            "Get user list with zero page size",
            should_have_data=True  # Should default to reasonable size
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Pagination edge case tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_pagination_with_individual_user(self) -> bool:
        """Test that individual user endpoints don't have pagination"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Individual user should not have pagination in response
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}", 
            "Get individual user (no pagination)",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: Individual user with page parameter (should be ignored)
        tests_total += 1
        if self.test_api_call(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}?page=2&pageSize=10", 
            "Get individual user with pagination params",
            should_have_data=True
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Individual user pagination tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def run_all_tests(self) -> bool:
        """Run all pagination tests"""
        if self.verbose:
            print(f"\n🧪 PAGINATION TESTS - {self.mode_name}")
            print("=" * 60)
        
        # Write curl commands (only for first mode)
        
        # Run tests
        test1_result = self.test_basic_pagination()
        test2_result = self.test_pagination_edge_cases()
        test3_result = self.test_pagination_with_individual_user()
        
        overall_success = test1_result and test2_result and test3_result
        
        if self.verbose:
            status = "✅ ALL PASS" if overall_success else "❌ SOME FAILED"
            print(f"\n{status} - Pagination Tests ({self.mode_name})")
            
        return overall_success

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pagination functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                       help='Server URL for API tests')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', action='store_true',
                       help='Write curl commands to curl.sh')
    args = parser.parse_args()
    
    print("🚀 Pagination Functionality Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print("=" * 50)
    
    tester = PaginationTester(args.config_file, args.server_url, args.verbose, args.curl, "Standalone")
    
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