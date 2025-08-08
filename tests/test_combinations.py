#!/usr/bin/env python3
"""
Combination parameter tests.
Tests API endpoints with multiple combined parameters (view + pagination + sorting + filtering).
"""

import sys
import asyncio
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import BaseTestFramework
from tests.test_case import TestCase
from tests.fixed_users import TEST_USERS
from tests.fixed_accounts import TEST_ACCOUNTS

class CombinationTester(BaseTestFramework):
    """Test combination parameter functionality"""
    
    def get_test_cases(self) -> List[TestCase]:
        """Return all test cases for this suite - single source of truth"""
        return [
            # View with pagination tests
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&pageSize=3", "Get user list with view and page size", 200, expected_paging=True),
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&page=1&pageSize=5", "Get user list with view and specific page", 200, expected_paging=True),
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&page=2&pageSize=3", "Get user list with view and second page", 200, expected_paging=True),
            
            # View with sorting tests
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=username", "Get user list with view and sorting", 200, expected_paging=True),
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&sort=-createdAt", "Get user list with view and reverse sorting", 200, expected_paging=True),
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=firstName,lastName", "Get user list with view and multi-field sorting", 200, expected_paging=True),
            
            # View with filtering tests
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true", "Get user list with view and filtering", 200, expected_paging=True),
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male,isAccountOwner:true", "Get user list with view and multiple filters", 200, expected_paging=True),
            TestCase("GET", f"/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=username:{TEST_USERS['valid_all']}", "Get user list with view and username filter", 200, expected_paging=True),
            
            # Pagination with sorting tests
            TestCase("GET", "/api/user?sort=username&pageSize=3", "Get user list with sorting and pagination", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=-createdAt&page=1&pageSize=5", "Get user list with reverse sorting and pagination", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=firstName&page=2&pageSize=3", "Get user list second page with sorting", 200, expected_paging=True),
            
            # Pagination with filtering tests
            TestCase("GET", "/api/user?filter=isAccountOwner:true&pageSize=3", "Get user list with filtering and pagination", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5", "Get user list with multiple filters and pagination", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=isAccountOwner:false&page=2&pageSize=3", "Get user list second page with filtering", 200, expected_paging=True),
            
            # Sorting with filtering tests
            TestCase("GET", "/api/user?filter=isAccountOwner:true&sort=username", "Get user list with filtering and sorting", 200, expected_paging=True, expected_filter={'isAccountOwner': 'true'}, expected_sort=[('username', 'asc')]),
            TestCase("GET", "/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt", "Get user list with multiple filters and reverse sorting", 200, expected_paging=True, expected_filter={'gender': 'male', 'isAccountOwner': 'false'}, expected_sort=[('createdAt', 'desc')]),
            TestCase("GET", "/api/user?filter=isAccountOwner:false&sort=firstName,lastName", "Get user list with filtering and multi-field sorting", 200, expected_paging=True, expected_filter={'isAccountOwner': 'false'}, expected_sort=[('firstName', 'asc'), ('lastName', 'asc')]),
            
            # All parameters combined tests
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true&sort=username&pageSize=3", "Get user list with all parameters combined", 200, expected_paging=True),
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male&sort=-createdAt&page=1&pageSize=5", "Get user list with all parameters different values", 200, expected_paging=True),
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22expiredAt%22%5D%7D&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10", "Get user list with complex parameter combination", 200, expected_paging=True),
        ]

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