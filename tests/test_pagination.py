#!/usr/bin/env python3
"""
Pagination tests.
Tests API endpoints with pagination parameters to verify proper page handling.
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import BaseTestFramework
from tests.test_case import TestCase
from tests.fixed_users import TEST_USERS
from tests.fixed_accounts import TEST_ACCOUNTS

class PaginationTester(BaseTestFramework):
    """Test pagination functionality"""
    
    def get_test_suite_name(self) -> str:
        """Return the display name for this test suite"""
        return "Pagination Tests"
    
    def get_test_cases(self) -> List[TestCase]:
        """Return all test cases for this suite - single source of truth"""
        return [
            # Basic pagination tests
            TestCase("GET", "/api/user", "Get user list with default pagination", 200, expected_paging=True),
            TestCase("GET", "/api/user?pageSize=3", "Get user list with page size 3", 200, expected_paging=True),
            TestCase("GET", "/api/user?page=1&pageSize=5", "Get user list page 1 with size 5", 200, expected_paging=True),
            TestCase("GET", "/api/user?page=2&pageSize=3", "Get user list page 2 with size 3", 200, expected_paging=True),
            # Edge case tests
            TestCase("GET", "/api/user?page=0&pageSize=5", "Get user list with page 0", 200, expected_paging=True),
            TestCase("GET", "/api/user?pageSize=100", "Get user list with large page size (framework test)", 200, expected_paging=True),
            TestCase("GET", "/api/user?pageSize=1000", "Get user list with very large page size (works in browser)", 200, expected_paging=True),
            TestCase("GET", "/api/user?page=999&pageSize=5", "Get user list beyond available pages", 200, expected_paging=True),
            TestCase("GET", "/api/user?pageSize=0", "Get user list with zero page size", 200, expected_paging=True),
            # Individual user tests
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}", "Get individual user (no pagination)", 200, expected_data_len=1),
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}?page=2&pageSize=10", "Get individual user with pagination params", 200, expected_data_len=1),
        ]

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