#!/usr/bin/env python3
"""
Combination parameter tests.
Tests API endpoints with multiple combined parameters (view + pagination + sorting + filtering).
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.suites.test_case import TestCase

class CombinationTester:
    """Static test suite for combination parameter functionality"""
    
    _test_cases = []
    
    @staticmethod
    def initialize():
        CombinationTester._test_cases = CombinationTester.get_test_cases()
    
    @classmethod
    def get_test_cases(cls) -> List[TestCase]:
        """Return TestCase objects - expected_response will be generated automatically"""
        if CombinationTester._test_cases:
            return CombinationTester._test_cases
            
        return [
            # View + Single Sort
            TestCase("GET", "User", "", "view=account(id)&sort=username", "View with single sort (username asc)", 200),
            TestCase("GET", "User", "", "view=account(id)&sort=-firstName", "View with single sort (firstName desc)", 200),
            TestCase("GET", "User", "", "view=account(id)&sort=dob", "View with date sort", 200),
            TestCase("GET", "User", "", "view=account(id)&sort=netWorth", "View with currency sort", 200),
            
            # View + Multiple Sort
            TestCase("GET", "User", "", "view=account(id)&sort=firstName,lastName", "View with multiple sort (names)", 200),
            TestCase("GET", "User", "", "view=account(id)&sort=-dob,firstName", "View with date desc then name sort", 200),
            TestCase("GET", "User", "", "view=account(id)&sort=gender,-netWorth", "View with enum then currency desc sort", 200),
            
            # View + Single Filter
            TestCase("GET", "User", "", "view=account(id)&filter=gender:male", "View with single filter (gender)", 200),
            TestCase("GET", "User", "", "view=account(id)&filter=isAccountOwner:true", "View with boolean filter", 200),
            TestCase("GET", "User", "", "view=account(id)&filter=netWorth:gte:50000", "View with currency range filter", 200),
            TestCase("GET", "User", "", "view=account(id)&filter=dob:gte:1990-01-01", "View with date range filter", 200),
            
            # View + Multiple Filter
            TestCase("GET", "User", "", "view=account(id)&filter=gender:male,isAccountOwner:true", "View with multiple filters", 200),
            TestCase("GET", "User", "", "view=account(id)&filter=dob:gte:1960-01-01,netWorth:gte:0", "View with date and currency filters", 200),
            TestCase("GET", "User", "", "view=account(id)&filter=gender:female,dob:lt:1995-01-01,isAccountOwner:false", "View with complex multiple filters", 200),
            
            # Pagination + Single Sort
            TestCase("GET", "User", "", "sort=username&pageSize=3", "Pagination with single sort", 200),
            TestCase("GET", "User", "", "sort=-dob&page=1&pageSize=5", "Pagination with date sort desc", 200),
            
            # Pagination + Multiple Sort
            TestCase("GET", "User", "", "sort=firstName,netWorth&pageSize=2", "Pagination with multiple sort", 200),
            TestCase("GET", "User", "", "sort=-gender,dob&page=2&pageSize=3", "Pagination with enum and date sort", 200),
            
            # Pagination + Single Filter
            TestCase("GET", "User", "", "filter=isAccountOwner:true&pageSize=3", "Pagination with boolean filter", 200),
            TestCase("GET", "User", "", "filter=dob:gte:1990-01-01&page=1&pageSize=2", "Pagination with date range filter", 200),
            
            # Pagination + Multiple Filter
            TestCase("GET", "User", "", "filter=gender:male,netWorth:gte:0&pageSize=3", "Pagination with multiple filters", 200),
            TestCase("GET", "User", "", "filter=isAccountOwner:true,dob:lt:2000-01-01&page=1&pageSize=2", "Pagination with complex filters", 200),
            
            # Sort + Single Filter
            TestCase("GET", "User", "", "sort=firstName&filter=gender:male", "Sort with single filter", 200),
            TestCase("GET", "User", "", "sort=-netWorth&filter=isAccountOwner:true", "Currency sort desc with boolean filter", 200),
            TestCase("GET", "User", "", "sort=dob&filter=netWorth:gte:0", "Date sort with currency filter", 200),
            
            # Sort + Multiple Filter
            TestCase("GET", "User", "", "sort=firstName&filter=gender:male,isAccountOwner:true", "Sort with multiple filters", 200),
            TestCase("GET", "User", "", "sort=-dob&filter=netWorth:gte:0,gender:female", "Date sort desc with mixed filters", 200),
            
            # Multiple Sort + Multiple Filter
            TestCase("GET", "User", "", "sort=firstName,netWorth&filter=gender:male,isAccountOwner:true", "Multiple sort with multiple filters", 200),
            TestCase("GET", "User", "", "sort=-dob,firstName&filter=netWorth:gte:50000,gender:female", "Complex sort with complex filters", 200),
            
            # All 4 parameters combined
            TestCase("GET", "User", "", "view=account(id)&sort=firstName&filter=gender:male&pageSize=3", "All parameters: view + sort + filter + pagination", 200),
            TestCase("GET", "User", "", "view=account(id)&sort=-dob,firstName&filter=isAccountOwner:true,netWorth:gte:0&page=1&pageSize=2", "All parameters with multiple sort/filter", 200),
            TestCase("GET", "User", "", "view=account(id)&sort=gender,-netWorth&filter=dob:gte:1960-01-01,dob:lt:2000-01-01&pageSize=5", "All parameters with date range filtering", 200),
            
            # Edge case combinations
            TestCase("GET", "User", "", "sort=firstName&filter=firstName:Valid", "Sort and filter by same field", 200),
            TestCase("GET", "User", "", "view=account(id)&filter=accountId:nonexistent_account_123456", "View with filter on FK field", 200),
        ]