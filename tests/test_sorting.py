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
from tests.fixed_accounts import TEST_ACCOUNTS

class SortingTester(BaseTestFramework):
    """Test sorting functionality"""
    
    @classmethod
    def initialize_test_cases(cls):
        """Create and register TestCase objects for this test suite"""
        from tests.data import BaseDataFactory
        test_cases = [
            # Single field sorting - String fields
            TestCase("GET", "user", "", "sort=username", "Sort by username ascending", 200),
            TestCase("GET", "user", "", "sort=-username", "Sort by username descending", 200),
            TestCase("GET", "user", "", "sort=firstName", "Sort by firstName ascending", 200),
            TestCase("GET", "user", "", "sort=-firstName", "Sort by firstName descending", 200),
            TestCase("GET", "user", "", "sort=lastName", "Sort by lastName ascending", 200),
            TestCase("GET", "user", "", "sort=-lastName", "Sort by lastName descending", 200),
            TestCase("GET", "user", "", "sort=email", "Sort by email ascending", 200),
            TestCase("GET", "user", "", "sort=-email", "Sort by email descending", 200),
            
            # Single field sorting - Currency/Numeric fields
            TestCase("GET", "user", "", "sort=netWorth", "Sort by netWorth ascending", 200),
            TestCase("GET", "user", "", "sort=-netWorth", "Sort by netWorth descending", 200),
            
            # Single field sorting - Date fields
            TestCase("GET", "user", "", "sort=dob", "Sort by date of birth ascending", 200),
            TestCase("GET", "user", "", "sort=-dob", "Sort by date of birth descending", 200),
            TestCase("GET", "user", "", "sort=createdAt", "Sort by createdAt ascending", 200),
            TestCase("GET", "user", "", "sort=-createdAt", "Sort by createdAt descending", 200),
            
            # Single field sorting - Boolean fields
            TestCase("GET", "user", "", "sort=isAccountOwner", "Sort by isAccountOwner ascending", 200),
            TestCase("GET", "user", "", "sort=-isAccountOwner", "Sort by isAccountOwner descending", 200),
            
            # Single field sorting - Enum fields
            TestCase("GET", "user", "", "sort=gender", "Sort by gender ascending", 200),
            TestCase("GET", "user", "", "sort=-gender", "Sort by gender descending", 200),
            
            # Multiple field sorting - Mixed data types
            TestCase("GET", "user", "", "sort=firstName,lastName", "Sort by firstName then lastName (both asc)", 200),
            TestCase("GET", "user", "", "sort=-firstName,lastName", "Sort by firstName desc then lastName asc", 200),
            TestCase("GET", "user", "", "sort=firstName,-lastName", "Sort by firstName asc then lastName desc", 200),
            TestCase("GET", "user", "", "sort=-firstName,-lastName", "Sort by firstName desc then lastName desc", 200),
            TestCase("GET", "user", "", "sort=dob,netWorth", "Sort by date then currency (both asc)", 200),
            TestCase("GET", "user", "", "sort=-dob,netWorth", "Sort by date desc then currency asc", 200),
            TestCase("GET", "user", "", "sort=gender,firstName,netWorth", "Sort by enum, string, then currency", 200),
            TestCase("GET", "user", "", "sort=isAccountOwner,-dob,firstName", "Sort by boolean, date desc, then string", 200),
            
            # Edge cases
            TestCase("GET", "user", "", "sort=createdAt,updatedAt", "Sort by auto-generated date fields", 200),
            TestCase("GET", "user", "", "sort=firstName,firstName", "Sort by same field twice (edge case)", 200),
            
            # Individual user with sort parameter (should be ignored)
            TestCase("GET", "user", "valid_all_user_123456", "sort=username", "Get individual user with sort parameter", 200),
        ]
        BaseDataFactory.register_test_cases('sort', test_cases)
    
    def get_test_cases(self) -> List[TestCase]:
        """Return pre-created test cases - pure retrieval"""
        from tests.data import BaseDataFactory
        return BaseDataFactory.get_test_cases('sort')

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sorting functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    args = parser.parse_args()
    
    print("🚀 Sorting Functionality Tests")
    print(f"Config: {args.config_file}")
    print("=" * 50)
    
    tester = SortingTester(args.config_file, verbose=args.verbose)
    
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