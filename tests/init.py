#!/usr/bin/env python3
"""
Test system initialization - single entry point for all test setup.
Call initialize_all() before running any tests.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

_initialized = False

def initialize_data():
    """Initialize all test data factories (step 1)"""
    print("🔧 Test data is static - no initialization needed")
    print("✅ Test data ready")

def initialize_suites():
    """Initialize all test suites (step 2)"""
    from tests.suites.test_basic import BasicAPITester
    from tests.suites.test_view import ViewParameterTester
    from tests.suites.test_pagination import PaginationTester
    from tests.suites.test_sorting import SortingTester
    from tests.suites.test_filtering import FilteringTester
    from tests.suites.test_combinations import CombinationTester
    from tests.suites.test_lowercase_params import LowercaseParamTester
    
    print("🔧 Initializing test suites...")
    BasicAPITester.initialize()
    ViewParameterTester.initialize()
    PaginationTester.initialize()
    SortingTester.initialize()
    FilteringTester.initialize()
    CombinationTester.initialize()
    LowercaseParamTester.initialize()
    print("✅ Test suites initialized")

def initialize_all():
    """Main entry point - initialize everything in correct order"""
    global _initialized
    if _initialized:
        return
    
    print("🚀 Initializing test system...")
    
    # Step 1: Data must be initialized first
    initialize_data()
    
    # Step 2: Suites can now safely create TestCase objects
    initialize_suites()
    
    _initialized = True
    print("✅ Test system ready")