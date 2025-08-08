#!/usr/bin/env python3
"""
Basic API functionality tests.
Tests fundamental GET /user/{id} and GET /user endpoints without additional parameters.
"""

import sys
import asyncio
from pathlib import Path
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import BaseTestFramework
from tests.test_case import TestCase
from tests.fixed_users import TEST_USERS, FixedUsers

# Removed hardcoded helper functions - using runtime data generation from base_test.py

class BasicAPITester(BaseTestFramework):
    """Test basic API functionality"""
    
    def get_test_cases(self) -> List[TestCase]:
        """Return all test cases for this suite - single source of truth"""
        return [
            # Individual user tests - using dynamic generation from fixed_users.py + metadata
            TestCase("GET", "user", TEST_USERS['valid_all'], '', "Get Valid user", 200, FixedUsers),
            TestCase("GET", "user", TEST_USERS['bad_enum'], '', "Get user with bad enum", 200, FixedUsers),
            TestCase("GET", "user", TEST_USERS['valid_all'], '', "Get valid user", 200, FixedUsers),
            TestCase("GET", "user", TEST_USERS['bad_enum'], '', "Get user with bad enum", 200, FixedUsers),
            TestCase("GET", "user", TEST_USERS['bad_currency'], '', "Get user with bad currency", 200, FixedUsers),
            TestCase("GET", "user", TEST_USERS['bad_fk'], '', "Get user with bad FK", 200, FixedUsers),
            TestCase("GET", "user", TEST_USERS['multiple_errors'], '', "Get user with multiple errors", 200, FixedUsers),
            TestCase("GET", "user", TEST_USERS['nonexistent'], '', "Get non-existent user", 404, FixedUsers),
            # User list tests
            TestCase("GET", "user", '', '', "Get user list", 200, FixedUsers),
            TestCase("GET", "user", '', "pageSize=3", "Get user list with page size", 200, FixedUsers)
        ]

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