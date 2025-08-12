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

# Removed hardcoded helper functions - using runtime data generation from base_test.py

class BasicAPITester(BaseTestFramework):
    """Test basic API functionality"""
    
    @classmethod
    def initialize_test_cases(cls):
        """Create and register TestCase objects for this test suite"""
        from tests.data import BaseDataFactory
        test_cases = [
            TestCase("GET", "user", "valid_all_user_123456", '', "Get Valid user", 200),
            TestCase("GET", "user", "bad_enum_user_123456", '', "Get user with bad enum", 200),
            TestCase("GET", "user", "bad_currency_user_123456", '', "Get user with bad currency", 200),
            TestCase("GET", "user", "bad_fk_user_123456", '', "Get user with bad FK", 200),
            TestCase("GET", "user", "multiple_errors_user_123456", '', "Get user with multiple errors", 200),
            TestCase("GET", "user", "nonexistent_user_123456", '', "Get non-existent user", 404),
            TestCase("GET", "user", '', '', "Get user list", 200),
            TestCase("GET", "user", '', "pageSize=3", "Get user list with page size", 200)
        ]
        BaseDataFactory.register_test_cases('basic', test_cases)
    
    def get_test_cases(self) -> List[TestCase]:
        """Return pre-created test cases - pure retrieval"""
        from tests.data import BaseDataFactory
        return BaseDataFactory.get_test_cases('basic')

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Basic API functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    args = parser.parse_args()
    
    print("🚀 Basic API Functionality Tests")
    print(f"Config: {args.config_file}")
    print("=" * 50)
    
    tester = BasicAPITester(args.config_file, verbose=args.verbose)
    
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