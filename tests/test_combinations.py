#!/usr/bin/env python3
"""
Combination parameter tests.
Tests API endpoints with multiple combined parameters (view + pagination + sorting + filtering).
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.common_test_framework import CommonTestFramework, TEST_USERS, TEST_ACCOUNTS

class CombinationTester(CommonTestFramework):
    """Test combination parameter functionality"""
    
    def test_view_with_pagination(self) -> bool:
        """Test view parameters combined with pagination"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: View with page size
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&pageSize=3", 
            "Get user list with view and page size",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: View with specific page
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&page=1&pageSize=5", 
            "Get user list with view and specific page",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 3: View with second page
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&page=2&pageSize=3", 
            "Get user list with view and second page",
            should_have_data=False  # May be empty
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 View with pagination tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_view_with_sorting(self) -> bool:
        """Test view parameters combined with sorting"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: View with basic sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=username", 
            "Get user list with view and sorting",
            should_have_data=True,
            validate_sort=[('username', 'asc')]
        ):
            tests_passed += 1
            
        # Test 2: View with reverse sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&sort=-createdAt", 
            "Get user list with view and reverse sorting",
            should_have_data=True,
            validate_sort=[('createdAt', 'desc')]
        ):
            tests_passed += 1
            
        # Test 3: View with multi-field sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=firstName,lastName", 
            "Get user list with view and multi-field sorting",
            should_have_data=True,
            validate_sort=[('firstName', 'asc'), ('lastName', 'asc')]
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 View with sorting tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_view_with_filtering(self) -> bool:
        """Test view parameters combined with filtering"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: View with basic filter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true", 
            "Get user list with view and filtering",
            should_have_data=False,  # May be empty
            validate_filter={'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 2: View with multiple filters
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male,isAccountOwner:true", 
            "Get user list with view and multiple filters",
            should_have_data=False,  # May be empty
            validate_filter={'gender': 'male', 'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 3: View with username filter (should find our test user)
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            f"/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=username:{TEST_USERS['valid_all']}", 
            "Get user list with view and username filter",
            should_have_data=True,  # Should find test user
            validate_filter={'username': TEST_USERS['valid_all']}
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 View with filtering tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_pagination_with_sorting(self) -> bool:
        """Test pagination combined with sorting"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Pagination with sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=username&pageSize=3", 
            "Get user list with sorting and pagination",
            should_have_data=True,
            validate_sort=[('username', 'asc')]
        ):
            tests_passed += 1
            
        # Test 2: Pagination with reverse sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=-createdAt&page=1&pageSize=5", 
            "Get user list with reverse sorting and pagination",
            should_have_data=True,
            validate_sort=[('createdAt', 'desc')]
        ):
            tests_passed += 1
            
        # Test 3: Second page with sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?sort=firstName&page=2&pageSize=3", 
            "Get user list second page with sorting",
            should_have_data=False,  # May be empty
            validate_sort=[('firstName', 'asc')]
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Pagination with sorting tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_pagination_with_filtering(self) -> bool:
        """Test pagination combined with filtering"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Pagination with filter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:true&pageSize=3", 
            "Get user list with filtering and pagination",
            should_have_data=False,  # May be empty
            validate_filter={'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 2: Pagination with multiple filters
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5", 
            "Get user list with multiple filters and pagination",
            should_have_data=False,  # May be empty
            validate_filter={'gender': 'male', 'isAccountOwner': 'false'}
        ):
            tests_passed += 1
            
        # Test 3: Second page with filter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:false&page=2&pageSize=3", 
            "Get user list second page with filtering",
            should_have_data=False,  # May be empty
            validate_filter={'isAccountOwner': 'false'}
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Pagination with filtering tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_sorting_with_filtering(self) -> bool:
        """Test sorting combined with filtering"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Sort with filter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:true&sort=username", 
            "Get user list with filtering and sorting",
            should_have_data=False,  # May be empty
            validate_sort=[('username', 'asc')],
            validate_filter={'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 2: Reverse sort with multiple filters
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt", 
            "Get user list with multiple filters and reverse sorting",
            should_have_data=False,  # May be empty
            validate_sort=[('createdAt', 'desc')],
            validate_filter={'gender': 'male', 'isAccountOwner': 'false'}
        ):
            tests_passed += 1
            
        # Test 3: Multi-field sort with filter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:false&sort=firstName,lastName", 
            "Get user list with filtering and multi-field sorting",
            should_have_data=False,  # May be empty
            validate_sort=[('firstName', 'asc'), ('lastName', 'asc')],
            validate_filter={'isAccountOwner': 'false'}
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Sorting with filtering tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_all_parameters_combined(self) -> bool:
        """Test all parameters combined together"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: All parameters with basic values
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true&sort=username&pageSize=3", 
            "Get user list with all parameters combined",
            should_have_data=False,  # May be empty
            validate_sort=[('username', 'asc')],
            validate_filter={'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 2: All parameters with different values
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male&sort=-createdAt&page=1&pageSize=5", 
            "Get user list with all parameters different values",
            should_have_data=False,  # May be empty
            validate_sort=[('createdAt', 'desc')],
            validate_filter={'gender': 'male'}
        ):
            tests_passed += 1
            
        # Test 3: All parameters with complex combinations
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22expiredAt%22%5D%7D&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10", 
            "Get user list with complex parameter combination",
            should_have_data=False,  # May be empty
            validate_sort=[('firstName', 'asc'), ('lastName', 'asc')],
            validate_filter={'isAccountOwner': 'false', 'gender': 'female'}
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 All parameters combined tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def run_all_tests(self) -> bool:
        """Run all combination tests"""
        if self.verbose:
            print(f"\n🧪 COMBINATION PARAMETER TESTS - {self.mode_name}")
            print("=" * 60)
        
        # Write curl commands (only for first mode)
        
        # Run tests
        test1_result = self.test_view_with_pagination()
        test2_result = self.test_view_with_sorting()
        test3_result = self.test_view_with_filtering()
        test4_result = self.test_pagination_with_sorting()
        test5_result = self.test_pagination_with_filtering()
        test6_result = self.test_sorting_with_filtering()
        test7_result = self.test_all_parameters_combined()
        
        overall_success = test1_result and test2_result and test3_result and test4_result and test5_result and test6_result and test7_result
        
        if self.verbose:
            status = "✅ ALL PASS" if overall_success else "❌ SOME FAILED"
            print(f"\n{status} - Combination Parameter Tests ({self.mode_name})")
            
        return overall_success

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Combination parameter functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                       help='Server URL for API tests')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', action='store_true',
                       help='Write curl commands to curl.sh')
    args = parser.parse_args()
    
    print("🚀 Combination Parameter Functionality Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print("=" * 50)
    
    tester = CombinationTester(args.config_file, args.server_url, args.verbose, args.curl, "Standalone")
    
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