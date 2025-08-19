#!/usr/bin/env python3
"""
Pagination tests.
Tests API endpoints with pagination parameters to verify proper page handling.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.suites.test_case import TestCase

class PaginationTester:
    """Static test suite for pagination functionality"""
    
    _test_cases = []
    
    @staticmethod
    def initialize():
        PaginationTester._test_cases = PaginationTester.get_test_cases()
    
    @classmethod
    def get_test_cases(cls) -> List[TestCase]:
        """Return TestCase objects - expected_response will be generated automatically"""
        if PaginationTester._test_cases:
            return PaginationTester._test_cases
            
        return [
            TestCase("GET", "User", "", "", "Get user list with default pagination", 200),
            TestCase("GET", "User", "", "pageSize=3", "Get user list with page size 3", 200),
            TestCase("GET", "User", "", "page=1&pageSize=5", "Get user list page 1 with size 5", 200),
            TestCase("GET", "User", "", "page=2&pageSize=3", "Get user list page 2 with size 3", 200),
            TestCase("GET", "User", "valid_all_user_123456", "", "Get individual user (no pagination)", 200),
            TestCase("GET", "User", "valid_all_user_123456", "page=2&pageSize=10", "Get individual user with pagination params", 200),
        ]
