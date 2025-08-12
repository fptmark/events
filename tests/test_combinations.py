#!/usr/bin/env python3
"""
Combination parameter tests.
Tests API endpoints with multiple combined parameters (view + pagination + sorting + filtering).
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

class CombinationTester(BaseTestFramework):
    """Test combination parameter functionality"""
    
    @classmethod
    def initialize_test_cases(cls):
        """Create and register TestCase objects for this test suite"""
        from tests.data import BaseDataFactory
        test_cases = [
            # View + Single Sort
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=username", "View with single sort (username asc)", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=-firstName", "View with single sort (firstName desc)", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=dob", "View with date sort", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=netWorth", "View with currency sort", 200),
            
            # View + Multiple Sort
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=firstName,lastName", "View with multiple sort (names)", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=-dob,firstName", "View with date desc then name sort", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=gender,-netWorth", "View with enum then currency desc sort", 200),
            
            # View + Single Filter
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=gender:male", "View with single filter (gender)", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true", "View with boolean filter", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=netWorth:gte:50000", "View with currency range filter", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=dob:gte:1990-01-01", "View with date range filter", 200),
            
            # View + Multiple Filter
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=gender:male,isAccountOwner:true", "View with multiple filters", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=dob:gte:1980-01-01,netWorth:gte:0", "View with date and currency filters", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=gender:female,dob:lt:1995-01-01,isAccountOwner:false", "View with complex multiple filters", 200),
            
            # Pagination + Single Sort
            TestCase("GET", "user", "", "sort=username&pageSize=3", "Pagination with single sort", 200),
            TestCase("GET", "user", "", "sort=-dob&page=1&pageSize=5", "Pagination with date sort desc", 200),
            
            # Pagination + Multiple Sort
            TestCase("GET", "user", "", "sort=firstName,netWorth&pageSize=2", "Pagination with multiple sort", 200),
            TestCase("GET", "user", "", "sort=-gender,dob&page=2&pageSize=3", "Pagination with enum and date sort", 200),
            
            # Pagination + Single Filter
            TestCase("GET", "user", "", "filter=isAccountOwner:true&pageSize=3", "Pagination with boolean filter", 200),
            TestCase("GET", "user", "", "filter=dob:gte:1990-01-01&page=1&pageSize=2", "Pagination with date range filter", 200),
            
            # Pagination + Multiple Filter
            TestCase("GET", "user", "", "filter=gender:male,netWorth:gte:0&pageSize=3", "Pagination with multiple filters", 200),
            TestCase("GET", "user", "", "filter=isAccountOwner:true,dob:lt:2000-01-01&page=1&pageSize=2", "Pagination with complex filters", 200),
            
            # Sort + Single Filter
            TestCase("GET", "user", "", "sort=firstName&filter=gender:male", "Sort with single filter", 200),
            TestCase("GET", "user", "", "sort=-netWorth&filter=isAccountOwner:true", "Currency sort desc with boolean filter", 200),
            TestCase("GET", "user", "", "sort=dob&filter=netWorth:gte:0", "Date sort with currency filter", 200),
            
            # Sort + Multiple Filter
            TestCase("GET", "user", "", "sort=firstName&filter=gender:male,isAccountOwner:true", "Sort with multiple filters", 200),
            TestCase("GET", "user", "", "sort=-dob&filter=netWorth:gte:0,gender:female", "Date sort desc with mixed filters", 200),
            
            # Multiple Sort + Multiple Filter
            TestCase("GET", "user", "", "sort=firstName,netWorth&filter=gender:male,isAccountOwner:true", "Multiple sort with multiple filters", 200),
            TestCase("GET", "user", "", "sort=-dob,firstName&filter=netWorth:gte:50000,gender:female", "Complex sort with complex filters", 200),
            
            # All 4 parameters combined
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=firstName&filter=gender:male&pageSize=3", "All parameters: view + sort + filter + pagination", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=-dob,firstName&filter=isAccountOwner:true,netWorth:gte:0&page=1&pageSize=2", "All parameters with multiple sort/filter", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=gender,-netWorth&filter=dob:gte:1980-01-01,dob:lt:2000-01-01&pageSize=5", "All parameters with date range filtering", 200),
            
            # Edge case combinations
            TestCase("GET", "user", "", "sort=firstName&filter=firstName:Valid", "Sort and filter by same field", 200),
            TestCase("GET", "user", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=accountId:nonexistent_account_123456", "View with filter on FK field", 200),
        ]
        BaseDataFactory.register_test_cases('combo', test_cases)
    
    def get_test_cases(self) -> List[TestCase]:
        """Return pre-created test cases - pure retrieval"""
        from tests.data import BaseDataFactory
        return BaseDataFactory.get_test_cases('combo')

async def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Combination parameter functionality tests')
    parser.add_argument('config_file', nargs='?', default='mongo.json',
                       help='Configuration file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    args = parser.parse_args()
    
    print("🚀 Combination Parameter Functionality Tests")
    print(f"Config: {args.config_file}")
    print("=" * 50)
    
    tester = CombinationTester(args.config_file, verbose=args.verbose)
    
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