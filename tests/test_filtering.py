#!/usr/bin/env python3
"""
Filtering tests.
Tests API endpoints with filter parameters to verify proper data filtering.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.common_test_framework import CommonTestFramework, TEST_USERS, TEST_ACCOUNTS

class FilteringTester(CommonTestFramework):
    """Test filtering functionality"""
    
    def test_basic_filtering(self) -> bool:
        """Test basic filtering parameters"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Filter by exact match
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=gender:male", 
            "Get user list filtered by gender male",
            should_have_data=False,  # May be empty
            validate_filter={'gender': 'male'}
        ):
            tests_passed += 1
            
        # Test 2: Filter by different field
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:true", 
            "Get user list filtered by isAccountOwner true",
            should_have_data=False,  # May be empty
            validate_filter={'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 3: Filter by string field
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            f"/api/user?filter=username:{TEST_USERS['valid_all']}", 
            "Get user list filtered by specific username",
            should_have_data=True,  # Should find our test user
            validate_filter={'username': TEST_USERS['valid_all']}
        ):
            tests_passed += 1
            
        # Test 4: Filter that returns no results
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=username:nonexistent_user_12345", 
            "Get user list filtered by nonexistent username",
            should_have_data=False  # Should be empty
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Basic filtering tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_multiple_filters(self) -> bool:
        """Test filtering by multiple criteria"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Multiple filters (AND logic)
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=gender:male,isAccountOwner:true", 
            "Get user list with multiple filters",
            should_have_data=False,  # May be empty
            validate_filter={'gender': 'male', 'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 2: Different combination of filters
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=gender:female,isAccountOwner:false", 
            "Get user list with different filter combination",
            should_have_data=False,  # May be empty
            validate_filter={'gender': 'female', 'isAccountOwner': 'false'}
        ):
            tests_passed += 1
            
        # Test 3: Mix of field types in filters
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            f"/api/user?filter=isAccountOwner:true,username:{TEST_USERS['valid_all']}", 
            "Get user list with mixed field type filters",
            should_have_data=False,  # May be empty if test user doesn't match
            validate_filter={'isAccountOwner': 'true', 'username': TEST_USERS['valid_all']}
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Multiple filtering tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_filtering_with_pagination(self) -> bool:
        """Test filtering combined with pagination"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Filter with page size
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:true&pageSize=3", 
            "Get filtered user list with pagination",
            should_have_data=False,  # May be empty
            validate_filter={'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 2: Filter with specific page
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=gender:male&page=1&pageSize=5", 
            "Get filtered user list with specific page",
            should_have_data=False,  # May be empty
            validate_filter={'gender': 'male'}
        ):
            tests_passed += 1
            
        # Test 3: Filter with second page
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:false&page=2&pageSize=3", 
            "Get filtered user list second page",
            should_have_data=False,  # May be empty
            validate_filter={'isAccountOwner': 'false'}
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Filtering with pagination tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_filtering_with_sorting(self) -> bool:
        """Test filtering combined with sorting"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Filter with sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:true&sort=username", 
            "Get filtered user list with sorting",
            should_have_data=False,  # May be empty
            validate_sort=[('username', 'asc')],
            validate_filter={'isAccountOwner': 'true'}
        ):
            tests_passed += 1
            
        # Test 2: Filter with reverse sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=gender:male&sort=-createdAt", 
            "Get filtered user list with reverse sorting",
            should_have_data=False,  # May be empty
            validate_sort=[('createdAt', 'desc')],
            validate_filter={'gender': 'male'}
        ):
            tests_passed += 1
            
        # Test 3: Filter with multiple field sort
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=isAccountOwner:false&sort=firstName,lastName", 
            "Get filtered user list with multi-field sorting",
            should_have_data=False,  # May be empty
            validate_sort=[('firstName', 'asc'), ('lastName', 'asc')],
            validate_filter={'isAccountOwner': 'false'}
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Filtering with sorting tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_invalid_filtering(self) -> bool:
        """Test invalid filtering parameters"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Filter by non-existent field (should handle gracefully)
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=nonexistentfield:value", 
            "Get user list with invalid filter field",
            should_have_data=True  # Should still return data, ignore bad filter
        ):
            tests_passed += 1
            
        # Test 2: Malformed filter parameter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=invalidformat", 
            "Get user list with malformed filter",
            should_have_data=True  # Should handle gracefully
        ):
            tests_passed += 1
            
        # Test 3: Empty filter parameter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            "/api/user?filter=", 
            "Get user list with empty filter parameter",
            should_have_data=True
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Invalid filtering tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def test_filtering_with_individual_user(self) -> bool:
        """Test that individual user endpoints ignore filtering"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Individual user should ignore filter parameter
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}?filter=gender:male", 
            "Get individual user with filter parameter",
            should_have_data=True
        ):
            tests_passed += 1
            
        # Test 2: Individual user with complex filter (should be ignored)
        tests_total += 1
        if self.test_api_call_with_validation(
            "GET", 
            f"/api/user/{TEST_USERS['valid_all']}?filter=gender:male,isAccountOwner:true", 
            "Get individual user with complex filter parameter",
            should_have_data=True
        ):
            tests_passed += 1
        
        if self.verbose:
            print(f"  📊 Individual user filtering tests: {tests_passed}/{tests_total} passed")
            
        return tests_passed == tests_total
    
    def run_all_tests(self) -> bool:
        """Run all filtering tests"""
        if self.verbose:
            print(f"\n🧪 FILTERING TESTS - {self.mode_name}")
            print("=" * 60)
        
        # Write curl commands (only for first mode)
        
        # Run tests
        test1_result = self.test_basic_filtering()
        test2_result = self.test_multiple_filters()
        test3_result = self.test_filtering_with_pagination()
        test4_result = self.test_filtering_with_sorting()
        test5_result = self.test_invalid_filtering()
        test6_result = self.test_filtering_with_individual_user()
        
        overall_success = test1_result and test2_result and test3_result and test4_result and test5_result and test6_result
        
        if self.verbose:
            status = "✅ ALL PASS" if overall_success else "❌ SOME FAILED"
            print(f"\n{status} - Filtering Tests ({self.mode_name})")
            
        return overall_success

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Filtering functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                       help='Server URL for API tests')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', action='store_true',
                       help='Write curl commands to curl.sh')
    args = parser.parse_args()
    
    print("🚀 Filtering Functionality Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print("=" * 50)
    
    tester = FilteringTester(args.config_file, args.server_url, args.verbose, args.curl, "Standalone")
    
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