#!/usr/bin/env python3
"""
View parameter tests.
Tests API endpoints with view parameters to verify FK sub-object population.
"""

import sys
import asyncio
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import BaseTestFramework
from tests.test_case import TestCase
from tests.fixed_users import TEST_USERS, FixedUsers
from tests.fixed_accounts import TEST_ACCOUNTS

# Removed hardcoded helper functions - using runtime data generation from base_test.py

class ViewParameterTester(BaseTestFramework):
    """Test view parameter functionality"""
    
    def get_test_cases(self) -> List[TestCase]:
        """Return all test cases for this suite - single source of truth"""
        return [
            # Individual user tests with view parameters - using dynamic generation from fixed_users.py + metadata
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get valid user with account ID view", 200, expected_data_len=1),
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", "Get valid user with full account view", 200, expected_data_len=1),
            TestCase("GET", f"/api/user/{TEST_USERS['bad_fk']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user with bad FK and account view", 200,
                expected_response=self.generate_expected_response("User", "bad_fk_user_123456", FixedUsers, 
                    view_objects={"account": {"exists": False}})),
            TestCase("GET", f"/api/user/{TEST_USERS['multiple_errors']}?view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user with multiple errors and account view", 200,
                expected_response=self.generate_expected_response("User", "multiple_errors_user_123456", FixedUsers,
                    view_objects={"account": {"exists": False}})),
            TestCase("GET", f"/api/user/{TEST_USERS['valid_all']}?view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D", "Get valid user with invalid view field", 200, expected_data_len=1),
            # User list tests with view parameters
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user list with account ID view", 200, expected_paging=True),
            TestCase("GET", "/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", "Get user list with full account view", 200, expected_paging=True),
            TestCase("GET", "/api/user?pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user list with pagination and view", 200, expected_paging=True),
        ]

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='View parameter functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                       help='Server URL for API tests')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', action='store_true',
                       help='Write curl commands to curl.sh')
    args = parser.parse_args()
    
    print("🚀 View Parameter Functionality Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print("=" * 50)
    
    tester = ViewParameterTester(args.config_file, args.server_url, args.verbose, args.curl, "Standalone")
    
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