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

# BaseTestFramework import removed - no longer needed
from .test_case import TestCase

# Removed hardcoded helper functions - using runtime data generation from base_test.py

class BasicAPITester:
    """Static test suite for basic API functionality"""
    
    # Static storage for initialized test cases
    _test_cases:List[TestCase] = []
    
    @staticmethod
    def initialize():
        """Initialize test cases - call once at startup"""
        BasicAPITester._test_cases = BasicAPITester.get_test_cases()
    
    @classmethod
    def get_test_cases(cls):
        """Return TestCase objects from UserDataFactory"""
        if BasicAPITester._test_cases:
            return BasicAPITester._test_cases
            
        from tests.data.user_data import UserDataFactory
        return UserDataFactory.get_test_cases()
