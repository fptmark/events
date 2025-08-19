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
from .test_case import TestCase

# Removed hardcoded helper functions - using runtime data generation from base_test.py

class BasicAPITester:
    """Static test suite for basic API functionality"""
    
    # Static storage for initialized test cases
    _test_cases = []
    
    @staticmethod
    def initialize():
        """Initialize test cases - call once at startup"""
        BasicAPITester._test_cases = BasicAPITester.get_test_cases()
    
    @classmethod
    def get_test_cases(cls):
        """Return TestCase objects - expected_response will be generated automatically"""
        if BasicAPITester._test_cases:
            return BasicAPITester._test_cases
            
        return [
            TestCase("GET", "User", "valid_all_user_123456", '', "Get Valid user", 200),
            TestCase("GET", "User", "bad_enum_user_123456", '', "Get user with bad enum", 200),
            TestCase("GET", "User", "bad_currency_user_123456", '', "Get user with bad currency", 200),
            TestCase("GET", "User", "bad_fk_user_123456", '', "Get user with bad FK", 200),
            TestCase("GET", "User", "multiple_errors_user_123456", '', "Get user with multiple errors", 200),
            TestCase("GET", "User", "nonexistent_user_123456", '', "Get non-existent user", 404),
            TestCase("GET", "User", '', '', "Get user list", 200),
            TestCase("GET", "user", '', "pageSize=3", "Get user list with page size", 200)
        ]
