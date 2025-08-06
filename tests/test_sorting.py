#!/usr/bin/env python3
"""
Sorting tests.
Tests API endpoints with sorting parameters to verify proper sort order.
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

class SortingTester(BaseTestFramework):
    """Test sorting functionality"""
    
    def get_test_cases(self) -> List[TestCase]:
        """Return all test cases for this suite - single source of truth"""
        return [
            # Basic sorting tests
            TestCase("GET", "/api/user?sort=username", "Get user list sorted by username ascending", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=-username", "Get user list sorted by username descending", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=createdAt", "Get user list sorted by createdAt ascending", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=-createdAt", "Get user list sorted by createdAt descending", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=firstName", "Get user list sorted by firstName ascending", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=-firstName", "Get user list sorted by firstName descending", 200, expected_paging=True),
            # Multiple field sorting tests
            TestCase("GET", "/api/user?sort=firstName,username", "Get user list sorted by firstName then username", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=-firstName,username", "Get user list sorted by firstName desc then username asc", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=firstName,-username", "Get user list sorted by firstName asc then username desc", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=-firstName,-username", "Get user list sorted by firstName desc then username desc", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=createdAt,firstName,username", "Get user list sorted by three fields", 200, expected_paging=True),
            # Sorting with pagination tests
            TestCase("GET", "/api/user?sort=firstName&pageSize=3", "Get user list sorted by firstName with pagination", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=-createdAt&page=2&pageSize=5", "Get user list sorted by createdAt desc with pagination", 200, expected_paging=True),
            # Invalid sorting tests
            TestCase("GET", "/api/user?sort=nonexistentfield", "Get user list with invalid sort field", 200, expected_paging=True),
            TestCase("GET", "/api/user?sort=", "Get user list with empty sort parameter", 200, expected_paging=True), 
            TestCase("GET", "/api/user?sort=-", "Get user list with malformed sort parameter", 200, expected_paging=True),
            # Individual user sorting tests
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}?sort=username", "Get individual user with sort parameter", 200, expected_data_len=1),
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}?sort=-createdAt,firstName", "Get individual user with complex sort parameter", 200, expected_data_len=1),
        ]

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