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
            TestCase("GET", "User", "valid_all_user_123456", "view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get valid user with account ID view", 200),
            TestCase("GET", "User", "valid_all_user_123456", "view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", "Get valid user with full account view", 200),
            TestCase("GET", "User", "bad_fk_user_123456", "view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user with bad FK and account view", 200, view_objects={"account": {"exists": False}}),
            TestCase("GET", "User", "multiple_errors_user_123456", "view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user with multiple errors and account view", 200, view_objects={"account": {"exists": False}}),
            TestCase("GET", "User", "valid_all_user_123456", "view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D", "Get valid user with invalid view field", 200),
            TestCase("GET", "User", "", "view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user list with account ID view", 200),
            TestCase("GET", "User", "", "view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D", "Get user list with full account view", 200),
            TestCase("GET", "User", "", "pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D", "Get user list with pagination and view", 200),
        ]