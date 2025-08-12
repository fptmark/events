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
            # Single field filtering - String fields (partial/wildcard matching)
            TestCase("GET", "user", "", "filter=username:valid_all_user", "Filter by username (contains match)", 200),
            TestCase("GET", "user", "", "filter=firstName:Valid", "Filter by firstName (contains 'Valid')", 200),
            TestCase("GET", "user", "", "filter=lastName:User", "Filter by lastName (contains 'User')", 200),
            TestCase("GET", "user", "", "filter=email:valid_all@test.com", "Filter by email (contains match)", 200),
            
            # Single field filtering - Boolean fields
            TestCase("GET", "user", "", "filter=isAccountOwner:true", "Filter by isAccountOwner true", 200),
            TestCase("GET", "user", "", "filter=isAccountOwner:false", "Filter by isAccountOwner false", 200),
            
            # Single field filtering - Enum fields
            TestCase("GET", "user", "", "filter=gender:male", "Filter by gender male", 200),
            TestCase("GET", "user", "", "filter=gender:female", "Filter by gender female", 200),
            TestCase("GET", "user", "", "filter=gender:invalid_gender", "Filter by invalid gender (edge case)", 200),
            
            # Single field filtering - Currency/Numeric fields
            TestCase("GET", "user", "", "filter=netWorth:50000.0", "Filter by netWorth exact match", 200),
            TestCase("GET", "user", "", "filter=netWorth:75000.0", "Filter by different netWorth value", 200),
            TestCase("GET", "user", "", "filter=netWorth:-5000.0", "Filter by negative netWorth", 200),
            
            # Date filtering - Exact dates
            TestCase("GET", "user", "", "filter=dob:1985-06-15", "Filter by exact date of birth", 200),
            TestCase("GET", "user", "", "filter=dob:1992-03-20", "Filter by different exact date", 200),
            
            # Date filtering - Comparison operators (exclude null dates)
            TestCase("GET", "user", "", "filter=dob:gte:1970-01-01", "Filter by dob greater than or equal 1970 (broader range)", 200),
            TestCase("GET", "user", "", "filter=dob:lte:2010-12-31", "Filter by dob less than or equal 2010 (broader range)", 200),
            TestCase("GET", "user", "", "filter=dob:gt:1970-01-01", "Filter by dob greater than 1970 (broader range)", 200),
            TestCase("GET", "user", "", "filter=dob:lt:2010-01-01", "Filter by dob less than 2010 (broader range)", 200),
            TestCase("GET", "user", "", "filter=netWorth:gte:50000", "Filter by netWorth greater than or equal 50k", 200),
            TestCase("GET", "user", "", "filter=netWorth:lt:0", "Filter by negative netWorth using comparison", 200),
            
            # Date filtering - Range using multiple comparisons (broader ranges)
            TestCase("GET", "user", "", "filter=dob:gte:1970-01-01,dob:lte:2010-12-31", "Filter by dob range 1970-2010 (broader)", 200),
            TestCase("GET", "user", "", "filter=netWorth:gte:-10000,netWorth:lte:100000", "Filter by netWorth range (including negatives)", 200),
            
            # Multiple field filtering - Mixed data types
            TestCase("GET", "user", "", "filter=gender:male,isAccountOwner:true", "Filter by gender and account owner", 200),
            TestCase("GET", "user", "", "filter=gender:female,netWorth:75000.0", "Filter by gender and netWorth", 200),
            TestCase("GET", "user", "", "filter=isAccountOwner:true,dob:gte:1985-01-01", "Filter by boolean and date range", 200),
            TestCase("GET", "user", "", "filter=firstName:Valid,lastName:User,gender:male", "Filter by multiple strings and enum", 200),
            TestCase("GET", "user", "", "filter=gender:female,netWorth:gte:70000,isAccountOwner:false", "Filter by enum, currency range, and boolean", 200),
            
            # Complex multiple criteria (adjusted ranges)
            TestCase("GET", "user", "", "filter=dob:gte:1970-01-01,dob:lt:2000-01-01,gender:male", "Filter by broader date range and gender", 200),
            TestCase("GET", "user", "", "filter=netWorth:gte:-10000,isAccountOwner:true,gender:male", "Filter by netWorth (including negatives), account owner, and gender", 200),
            
            # Edge cases
            TestCase("GET", "user", "", "filter=firstName:NonExistent", "Filter by non-existent value", 200),
            TestCase("GET", "user", "", "filter=netWorth:0", "Filter by zero netWorth", 200),
            TestCase("GET", "user", "", "filter=dob:2050-01-01", "Filter by future date (no matches)", 200),
            TestCase("GET", "user", "", "filter=gender:male,gender:female", "Filter by contradictory values (edge case)", 200),
            
            # Individual user with filter parameter (should be ignored)
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