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
from tests.fixed_accounts import TEST_ACCOUNTS

class PaginationTester(BaseTestFramework):
    """Test pagination functionality"""
    
    def get_test_suite_name(self) -> str:
        """Return the display name for this test suite"""
        return "Pagination Tests"
    
    @classmethod
    def initialize_test_cases(cls):
        """Create and register TestCase objects for this test suite"""
        from tests.data import BaseDataFactory
        test_cases = [
            TestCase("GET", "user", "", "", "Get user list with default pagination", 200),
            TestCase("GET", "user", "", "pageSize=3", "Get user list with page size 3", 200),
            TestCase("GET", "user", "", "page=1&pageSize=5", "Get user list page 1 with size 5", 200),
            TestCase("GET", "user", "", "page=2&pageSize=3", "Get user list page 2 with size 3", 200),
            TestCase("GET", "user", "valid_all_user_123456", "", "Get individual user (no pagination)", 200),
            TestCase("GET", "user", "valid_all_user_123456", "page=2&pageSize=10", "Get individual user with pagination params", 200),
        ]
        BaseDataFactory.register_test_cases('page', test_cases)
    
    def get_test_cases(self) -> List[TestCase]:
        """Return pre-created test cases - pure retrieval"""
        from tests.data import BaseDataFactory
        return BaseDataFactory.get_test_cases('page')

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pagination functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    args = parser.parse_args()
    
    print("🚀 Pagination Functionality Tests")
    print(f"Config: {args.config_file}")
    print("=" * 50)
    
    tester = PaginationTester(args.config_file, verbose=args.verbose)
    
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