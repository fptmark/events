#!/usr/bin/env python3
"""
View parameter tests.
Tests API endpoints with view parameters to verify FK sub-object population.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.suites.test_case import TestCase

class ViewParameterTester:
    """Static test suite for view parameter functionality"""
    
    _test_cases = []
    
    @staticmethod
    def initialize():
        ViewParameterTester._test_cases = ViewParameterTester.get_test_cases()
    
    @classmethod
    def get_test_cases(cls) -> List[TestCase]:
        """Return TestCase objects - expected_response will be generated automatically"""
        if ViewParameterTester._test_cases:
            return ViewParameterTester._test_cases
            
        return [
            TestCase("GET", "User", "valid_user_1", "view=account(id)", "Get valid user with account ID view", 200),
            TestCase("GET", "User", "valid_user_1", "view=account(id,createdAt,expiredAt)", "Get valid user with full account view", 200),
            TestCase("GET", "User", "bad_fk_user_123456", "view=account(id)", "Get user with bad FK and account view", 200, view_objects={"account": {"exists": False}}),
            TestCase("GET", "User", "multiple_errors_user_123456", "view=account(id)", "Get user with multiple errors and account view", 200, view_objects={"account": {"exists": False}}),
            TestCase("GET", "User", "valid_user_1", "view=account(nonexistent_field)", "Get valid user with invalid view field", 200),
            TestCase("GET", "User", "", "view=account(id)", "Get user list with account ID view", 200),
            TestCase("GET", "User", "", "view=account(id,createdAt,expiredAt)", "Get user list with full account view", 200),
            TestCase("GET", "User", "", "view=badentity(id,createdAt,expiredAt)", "Get user list with bad fk", 400),
            TestCase("GET", "User", "", "view=account(id,createdAt,badfield)", "Get user list with bad account field", 400),
            TestCase("GET", "User", "", "pageSize=3&view=account(id)", "Get user list with pagination and view", 200),
        ]