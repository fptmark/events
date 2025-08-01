#!/usr/bin/env python3
"""
Sorting tests.
Tests API endpoints with sorting parameters to verify proper sort order.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.common_test_framework import CommonTestFramework, TEST_USERS, TEST_ACCOUNTS

class SortingTester(CommonTestFramework):
    """Test sorting functionality"""
    
    def test_basic_sorting(self) -> bool:
        """Test basic sorting parameters"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Sort by username ascending
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=username", 
            "Get user list sorted by username ascending",
            should_have_data=True,
            validate_sort=[('username', 'asc')]
        ):
            tests_passed += 1
            
        # Test 2: Sort by username descending
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=-username", 
            "Get user list sorted by username descending",
            should_have_data=True,
            validate_sort=[('username', 'desc')]
        ):
            tests_passed += 1
            
        # Test 3: Sort by createdAt ascending
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=createdAt", 
            "Get user list sorted by createdAt ascending",
            should_have_data=True,
            validate_sort=[('createdAt', 'asc')]
        ):
            tests_passed += 1
            
        # Test 4: Sort by createdAt descending
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=-createdAt", 
            "Get user list sorted by createdAt descending",
            should_have_data=True,
            validate_sort=[('createdAt', 'desc')]
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Basic sorting tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_multiple_field_sorting(self) -> bool:
        """Test sorting by multiple fields"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Sort by multiple fields
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=firstName,lastName", 
            "Get user list sorted by firstName and lastName",
            should_have_data=True,
            validate_sort=[('firstName', 'asc'), ('lastName', 'asc')]
        ):
            tests_passed += 1
            
        # Test 2: Sort by mixed ascending/descending
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=firstName,-createdAt", 
            "Get user list sorted by firstName asc, createdAt desc",
            should_have_data=True,
            validate_sort=[('firstName', 'asc'), ('createdAt', 'desc')]
        ):
            tests_passed += 1
            
        # Test 3: Sort by multiple fields with different order
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=-lastName,firstName", 
            "Get user list sorted by lastName desc, firstName asc",
            should_have_data=True,
            validate_sort=[('lastName', 'desc'), ('firstName', 'asc')]
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Multiple field sorting tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_sorting_with_pagination(self) -> bool:
        """Test sorting combined with pagination"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Sort with page size
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=username&pageSize=3", 
            "Get user list sorted with pagination",
            should_have_data=True,
            validate_sort=[('username', 'asc')]
        ):
            tests_passed += 1
            
        # Test 2: Sort with specific page
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=-createdAt&page=1&pageSize=5", 
            "Get user list sorted with specific page",
            should_have_data=True,
            validate_sort=[('createdAt', 'desc')]
        ):
            tests_passed += 1
            
        # Test 3: Sort with second page
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=firstName&page=2&pageSize=3", 
            "Get user list sorted second page",
            should_have_data=False,  # May be empty if not enough users
            validate_sort=[('firstName', 'asc')]
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Sorting with pagination tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_invalid_sorting(self) -> bool:
        """Test invalid sorting parameters"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Sort by non-existent field (should handle gracefully - no sort validation)
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=nonexistentfield", 
            "Get user list with invalid sort field",
            should_have_data=True  # Should still return data, ignore bad sort
        ):
            tests_passed += 1
            
        # Test 2: Empty sort parameter (no sort validation)
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=", 
            "Get user list with empty sort parameter",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 3: Malformed sort parameter (no sort validation)
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=-", 
            "Get user list with malformed sort parameter",
            should_have_data=True
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Invalid sorting tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_sorting_with_individual_user(self) -> bool:
        """Test that individual user endpoints ignore sorting"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Individual user should ignore sort parameter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}?sort=username", 
            "Get individual user with sort parameter",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: Individual user with complex sort (should be ignored)
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}?sort=-createdAt,firstName", 
            "Get individual user with complex sort parameter",
            should_have_data=True
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Individual user sorting tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def run_all_tests(self) -> bool:
        """Run all sorting tests"""
        if self.verbose:
            print(f"\n🧪 SORTING TESTS - {self.mode_name}")
            print("=" * 60)
        
        # Write curl commands (only for first mode)
        
        # Run tests
        test1_result = self.test_basic_sorting()
        test2_result = self.test_multiple_field_sorting()
        test3_result = self.test_sorting_with_pagination()
        test4_result = self.test_invalid_sorting()
        test5_result = self.test_sorting_with_individual_user()
        
        overall_success = test1_result and test2_result and test3_result and test4_result and test5_result
        
        if self.verbose:
            status = "✅ ALL PASS" if overall_success else "❌ SOME FAILED"
            print(f"\n{status} - Sorting Tests ({self.mode_name})")
            
        return overall_success

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sorting functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                       help='Server URL for API tests')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', action='store_true',
                       help='Write curl commands to curl.sh')
    args = parser.parse_args()
    
    print("🚀 Sorting Functionality Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print("=" * 50)
    
    tester = SortingTester(args.config_file, args.server_url, args.verbose, args.curl, "Standalone")
    
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