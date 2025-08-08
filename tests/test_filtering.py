#!/usr/bin/env python3
"""
Filtering tests.
Tests API endpoints with filter parameters to verify proper data filtering.
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

class FilteringTester(BaseTestFramework):
    """Test filtering functionality"""
    
    def get_test_cases(self) -> List[TestCase]:
        """Return all test cases for this suite - single source of truth"""
        return [
            # Basic filtering tests
            TestCase("GET", "/api/user?filter=gender:male", "Get user list filtered by gender male", 200, expected_paging=True, expected_filter={'gender': 'male'}),
            TestCase("GET", "/api/user?filter=isAccountOwner:true", "Get user list filtered by isAccountOwner true", 200, expected_paging=True, expected_filter={'isAccountOwner': 'true'}),
            TestCase("GET", f"/api/user?filter=username:{TEST_USERS['valid_all']}", "Get user list filtered by specific username", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=username:nonexistent_user_12345", "Get user list filtered by nonexistent username", 200, expected_paging=True),
            # Multiple filters
            TestCase("GET", "/api/user?filter=gender:male,isAccountOwner:true", "Get user list with multiple filters", 200, expected_paging=True, expected_filter={'gender': 'male', 'isAccountOwner': 'true'}),
            TestCase("GET", "/api/user?filter=gender:female,isAccountOwner:false", "Get user list with different filter combination", 200, expected_paging=True, expected_filter={'gender': 'female', 'isAccountOwner': 'false'}),
            TestCase("GET", f"/api/user?filter=isAccountOwner:true,username:{TEST_USERS['valid_all']}", "Get user list with mixed field type filters", 200, expected_paging=True),
            # Filtering with pagination
            TestCase("GET", "/api/user?filter=isAccountOwner:true&pageSize=3", "Get filtered user list with pagination", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=gender:male&page=1&pageSize=5", "Get filtered user list with specific page", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=isAccountOwner:false&page=2&pageSize=3", "Get filtered user list second page", 200, expected_paging=True),
            # Filtering with sorting
            TestCase("GET", "/api/user?filter=isAccountOwner:true&sort=username", "Get filtered user list with sorting", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=gender:male&sort=-createdAt", "Get filtered user list with reverse sorting", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=isAccountOwner:false&sort=firstName,lastName", "Get filtered user list with multi-field sorting", 200, expected_paging=True),
            # Invalid filtering
            TestCase("GET", "/api/user?filter=nonexistentfield:value", "Get user list with invalid filter field", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=invalidformat", "Get user list with malformed filter", 200, expected_paging=True),
            TestCase("GET", "/api/user?filter=", "Get user list with empty filter parameter", 200, expected_paging=True),
            # Individual user with filters (should be ignored)
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}?filter=gender:male", "Get individual user with filter parameter", 200, expected_data_len=1),
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}?filter=gender:male,isAccountOwner:true", "Get individual user with complex filter parameter", 200, expected_data_len=1),
        ]

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