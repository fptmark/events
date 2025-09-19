#!/usr/bin/env python3
"""
Sorting tests.
Tests API endpoints with sorting parameters to verify proper sort order.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.suites.test_case import TestCase

class SortingTester:
    """Static test suite for sorting functionality"""
    
    _test_cases = []
    
    @staticmethod
    def initialize():
        SortingTester._test_cases = SortingTester.get_test_cases()
    
    @classmethod
    def get_test_cases(cls) -> List[TestCase]:
        """Return TestCase objects - expected_response will be generated automatically"""
        if SortingTester._test_cases:
            return SortingTester._test_cases
            
        return [
            # Single field sorting - String fields
            TestCase("GET", "User", "", "sort=username", "Sort by username ascending", 200),
            TestCase("GET", "User", "", "sort=username:desc", "Sort by username descending", 200),
            TestCase("GET", "User", "", "sort=firstName", "Sort by firstName ascending", 200),
            TestCase("GET", "User", "", "sort=firstName:desc", "Sort by firstName descending", 200),
            TestCase("GET", "User", "", "sort=lastName", "Sort by lastName ascending", 200),
            TestCase("GET", "User", "", "sort=lastName:desc", "Sort by lastName descending", 200),
            TestCase("GET", "User", "", "sort=email", "Sort by email ascending", 200),
            TestCase("GET", "User", "", "sort=email:desc", "Sort by email descending", 200),
            
            # Single field sorting - Currency/Numeric fields
            TestCase("GET", "User", "", "sort=netWorth", "Sort by netWorth ascending", 200),
            TestCase("GET", "User", "", "sort=netWorth:desc", "Sort by netWorth descending", 200),
            
            # Single field sorting - Date fields
            TestCase("GET", "User", "", "sort=dob", "Sort by date of birth ascending", 200),
            TestCase("GET", "User", "", "sort=dob:desc", "Sort by date of birth descending", 200),
            TestCase("GET", "User", "", "sort=createdAt", "Sort by createdAt ascending", 200),
            TestCase("GET", "User", "", "sort=createdAt:desc", "Sort by createdAt descending", 200),
            
            # Single field sorting - Boolean fields
            TestCase("GET", "User", "", "sort=isAccountOwner", "Sort by isAccountOwner ascending", 200),
            TestCase("GET", "User", "", "sort=isAccountOwner:desc", "Sort by isAccountOwner descending", 200),
            
            # Single field sorting - Enum fields
            TestCase("GET", "User", "", "sort=gender", "Sort by gender ascending", 200),
            TestCase("GET", "User", "", "sort=gender:desc", "Sort by gender descending", 200),
            
            # Multiple field sorting - Mixed data types
            TestCase("GET", "User", "", "sort=firstName,lastName", "Sort by firstName then lastName (both asc)", 200),
            TestCase("GET", "User", "", "sort=firstName:desc,lastName", "Sort by firstName desc then lastName asc", 200),
            TestCase("GET", "User", "", "sort=firstName,lastName:desc", "Sort by firstName asc then lastName desc", 200),
            TestCase("GET", "User", "", "sort=firstName:desc,lastName:desc", "Sort by firstName desc then lastName desc", 200),
            TestCase("GET", "User", "", "sort=dob,netWorth", "Sort by date then currency (both asc)", 200),
            TestCase("GET", "User", "", "sort=dob:desc,netWorth", "Sort by date desc then currency asc", 200),
            TestCase("GET", "User", "", "sort=gender,firstName,netWorth", "Sort by enum, string, then currency", 200),
            TestCase("GET", "User", "", "sort=isAccountOwner,dob:desc,firstName", "Sort by boolean, date desc, then string", 200),
            
            # Edge cases
            TestCase("GET", "User", "", "sort=dob,updatedAt", "Sort by dob + auto date fields", 200),
            TestCase("GET", "User", "", "sort=firstName,firstName", "Sort by same field twice (edge case)", 200),
            
            # Individual user with sort parameter (should be ignored)
            TestCase("GET", "User", "valid_all_user_123456", "sort=username", "Get individual user with sort parameter", 200),
        ]
