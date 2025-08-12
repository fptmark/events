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
from tests.fixed_accounts import TEST_ACCOUNTS

# Removed hardcoded helper functions - using runtime data generation from base_test.py

class ViewParameterTester(BaseTestFramework):
    """Test view parameter functionality"""
    
    @classmethod
    def initialize_test_cases(cls):
        """Create and register TestCase objects for this test suite"""
        from tests.data import BaseDataFactory
        test_cases = [
            TestCase("GET", "user", "valid_all_user_123456", "view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get valid user with account ID view", 200),
            TestCase("GET", "user", "valid_all_user_123456", "view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", "Get valid user with full account view", 200),
            TestCase("GET", "user", "bad_fk_user_123456", "view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user with bad FK and account view", 200, view_objects={"account": {"exists": False}}),
            TestCase("GET", "user", "multiple_errors_user_123456", "view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user with multiple errors and account view", 200, view_objects={"account": {"exists": False}}),
            TestCase("GET", "user", "valid_all_user_123456", "view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D", "Get valid user with invalid view field", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user list with account ID view", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", "Get user list with full account view", 200),
            TestCase("GET", "user", "", "pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user list with pagination and view", 200),
        ]
        BaseDataFactory.register_test_cases('view', test_cases)
    
    def get_test_cases(self) -> List[TestCase]:
        """Return pre-created test cases - pure retrieval"""
        from tests.data import BaseDataFactory
        return BaseDataFactory.get_test_cases('view')

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='View parameter functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    args = parser.parse_args()
    
    print("🚀 View Parameter Functionality Tests")
    print(f"Config: {args.config_file}")
    print("=" * 50)
    
    tester = ViewParameterTester(args.config_file, verbose=args.verbose)
    
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