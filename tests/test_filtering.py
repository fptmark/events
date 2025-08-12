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
from tests.fixed_accounts import TEST_ACCOUNTS

class FilteringTester(BaseTestFramework):
    """Test filtering functionality"""
    
    @classmethod
    def initialize_test_cases(cls):
        """Create and register TestCase objects for this test suite"""
        from tests.data import BaseDataFactory
        test_cases = [
            TestCase("GET", "user", "", "filter=gender:male", "Get user list filtered by gender male", 200, expected_filter={'gender': 'male'}),
            TestCase("GET", "user", "", "filter=isAccountOwner:true", "Get user list filtered by isAccountOwner true", 200, expected_filter={'isAccountOwner': 'true'}),
            TestCase("GET", "user", "", "filter=gender:male,isAccountOwner:true", "Get user list with multiple filters", 200, expected_filter={'gender': 'male', 'isAccountOwner': 'true'}),
            TestCase("GET", "user", "valid_all_user_123456", "filter=gender:male", "Get individual user with filter parameter", 200),
        ]
        BaseDataFactory.register_test_cases('filter', test_cases)
    
    def get_test_cases(self) -> List[TestCase]:
        """Return pre-created test cases - pure retrieval"""
        from tests.data import BaseDataFactory
        return BaseDataFactory.get_test_cases('filter')

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Filtering functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    args = parser.parse_args()
    
    print("🚀 Filtering Functionality Tests")
    print(f"Config: {args.config_file}")
    print("=" * 50)
    
    tester = FilteringTester(args.config_file, verbose=args.verbose)
    
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