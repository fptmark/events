#!/usr/bin/env python3
"""
Filtering tests.
Tests API endpoints with filter parameters to verify proper data filtering.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.suites.test_case import TestCase

class FilteringTester:
    """Static test suite for filtering functionality"""
    
    _test_cases = []
    
    @staticmethod
    def initialize():
        FilteringTester._test_cases = FilteringTester.get_test_cases()
    
    @classmethod
    def get_test_cases(cls) -> List[TestCase]:
        """Return TestCase objects - expected_response will be generated automatically"""
        if FilteringTester._test_cases:
            return FilteringTester._test_cases
            
        return [
            # Single field filtering - String fields (partial/wildcard matching)
            TestCase("GET", "User", "", "filter=username:valid_all_user", "Filter by username (contains match)", 200),
            TestCase("GET", "User", "", "filter=firstName:Valid", "Filter by firstName (contains 'Valid')", 200),
            TestCase("GET", "User", "", "filter=lastName:User", "Filter by lastName (contains 'User')", 200),
            TestCase("GET", "User", "", "filter=email:valid_all@test.com", "Filter by email (contains match)", 200),
            
            # Single field filtering - Boolean fields
            TestCase("GET", "User", "", "filter=isAccountOwner:true", "Filter by isAccountOwner true", 200),
            TestCase("GET", "User", "", "filter=isAccountOwner:false", "Filter by isAccountOwner false", 200),
            
            # Single field filtering - Enum fields
            TestCase("GET", "User", "", "filter=gender:male", "Filter by gender male", 200),
            TestCase("GET", "User", "", "filter=gender:female", "Filter by gender female", 200),
            TestCase("GET", "User", "", "filter=gender:invalid_gender", "Filter by invalid gender (edge case)", 200),
            
            # Single field filtering - Currency/Numeric fields
            TestCase("GET", "User", "", "filter=netWorth:50000.0", "Filter by netWorth exact match", 200),
            TestCase("GET", "User", "", "filter=netWorth:75000.0", "Filter by different netWorth value", 200),
            TestCase("GET", "User", "", "filter=netWorth:-5000.0", "Filter by negative netWorth", 200),
            
            # Date filtering - Exact dates
            TestCase("GET", "User", "", "filter=dob:1985-06-15", "Filter by exact date of birth", 200),
            TestCase("GET", "User", "", "filter=dob:1992-03-20", "Filter by different exact date", 200),
            
            # Date filtering - Comparison operators (exclude null dates)
            TestCase("GET", "User", "", "filter=dob:gte:1950-01-01", "Filter by dob greater than or equal 1950 (broader range)", 200),
            TestCase("GET", "User", "", "filter=dob:lte:2050-12-31", "Filter by dob less than or equal 2050 (broader range)", 200),
            TestCase("GET", "User", "", "filter=dob:gt:1950-01-01", "Filter by dob greater than 1950 (broader range)", 200),
            TestCase("GET", "User", "", "filter=dob:lt:2050-01-01", "Filter by dob less than 2050 (broader range)", 200),
            TestCase("GET", "User", "", "filter=netWorth:gte:50000", "Filter by netWorth greater than or equal 50k", 200),
            TestCase("GET", "User", "", "filter=netWorth:lt:0", "Filter by negative netWorth using comparison", 200),
            
            # Date filtering - Range using multiple comparisons (broader ranges)
            TestCase("GET", "User", "", "filter=dob:gte:1950-01-01,dob:lte:2050-12-31", "Filter by dob range 1950-2050 (broader)", 200),
            TestCase("GET", "User", "", "filter=netWorth:gte:-10000,netWorth:lte:100000", "Filter by netWorth range (including negatives)", 200),
            
            # Multiple field filtering - Mixed data types
            TestCase("GET", "User", "", "filter=gender:male,isAccountOwner:true", "Filter by gender and account owner", 200),
            TestCase("GET", "User", "", "filter=gender:female,netWorth:75000.0", "Filter by gender and netWorth", 200),
            TestCase("GET", "User", "", "filter=isAccountOwner:true,dob:gte:1960-01-01", "Filter by boolean and date range", 200),
            TestCase("GET", "User", "", "filter=firstName:Valid,lastName:User,gender:male", "Filter by multiple strings and enum", 200),
            TestCase("GET", "User", "", "filter=gender:female,netWorth:gte:70000,isAccountOwner:false", "Filter by enum, currency range, and boolean", 200),
            
            # Complex multiple criteria (adjusted ranges)
            TestCase("GET", "User", "", "filter=dob:gte:1950-01-01,dob:lt:2000-01-01,gender:male", "Filter by broader date range and gender", 200),
            TestCase("GET", "User", "", "filter=netWorth:gte:-10000,isAccountOwner:true,gender:male", "Filter by netWorth (including negatives), account owner, and gender", 200),
            
            # Edge cases
            TestCase("GET", "User", "", "filter=firstName:NonExistent", "Filter by non-existent value", 200),
            TestCase("GET", "User", "", "filter=netWorth:0", "Filter by zero netWorth", 200),
            TestCase("GET", "User", "", "filter=dob:2050-01-01", "Filter by future date (no matches)", 200),
            TestCase("GET", "User", "", "filter=gender:male,gender:female", "Filter by contradictory values (edge case)", 200),
            
            # Individual user with filter parameter (should be ignored)
            TestCase("GET", "User", "valid_all_user_123456", "filter=gender:male", "Get individual user with filter parameter", 200),
        ]