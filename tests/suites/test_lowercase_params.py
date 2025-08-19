#!/usr/bin/env python3
"""
Lowercase parameter and field name tests.
Tests that server properly handles case-insensitive URL parameters and field names.
"""

import sys
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.suites.test_case import TestCase

class LowercaseParamTester:
    """Static test suite for case-insensitive parameter and field handling"""
    
    _test_cases = []
    
    @staticmethod
    def initialize():
        LowercaseParamTester._test_cases = LowercaseParamTester.get_test_cases()
    
    @classmethod
    def get_test_cases(cls) -> List[TestCase]:
        """Return TestCase objects - expected_response will be generated automatically"""
        if LowercaseParamTester._test_cases:
            return LowercaseParamTester._test_cases
            
        return [
            # Test standard URL parameters
            TestCase("GET", "User", "", "page_size=5", "page_size parameter", 200),
            TestCase("GET", "User", "", "page=1&page_size=3", "page_size with page", 200),
            
            # Test field names in sorting
            TestCase("GET", "User", "", "sort=firstname", "Sort by firstname", 200),
            TestCase("GET", "User", "", "sort=lastname,-createdat", "Sort by multiple fields", 200),
            TestCase("GET", "User", "", "sort=isaccountowner,firstname", "Sort by boolean and string", 200),
            
            # Test field names in filtering
            TestCase("GET", "User", "", "filter=gender:female", "Filter by gender field", 200),
            TestCase("GET", "User", "", "filter=firstname:test", "Filter by firstname", 200),
            TestCase("GET", "User", "", "filter=isaccountowner:true", "Filter by boolean field", 200),
            
            # Test number/currency range filtering (using actual User fields)
            TestCase("GET", "User", "", "filter=networth:gte:1000", "Filter networth greater than or equal", 200),
            TestCase("GET", "User", "", "filter=networth:gt:1000", "Filter networth greater than", 200),
            TestCase("GET", "User", "", "filter=networth:lt:100000", "Filter networth less than", 200),
            TestCase("GET", "User", "", "filter=networth:lte:100000", "Filter networth less than or equal", 200),
            
            # Test date range filtering
            TestCase("GET", "User", "", "filter=dob:gte:1990-01-01", "Filter date of birth greater than or equal", 200),
            TestCase("GET", "User", "", "filter=dob:lt:2000-01-01", "Filter date of birth less than", 200),
            TestCase("GET", "User", "", "filter=createdat:gte:2023-01-01", "Filter created date greater than or equal", 200),
            TestCase("GET", "User", "", "filter=createdat:lt:2024-01-01", "Filter created date less than", 200),
            TestCase("GET", "User", "", "filter=updatedat:gt:2023-06-01", "Filter updated date greater than", 200),
            TestCase("GET", "User", "", "filter=updatedat:lte:2024-12-31", "Filter updated date less than or equal", 200),
            
            # Test combined range filtering (using actual User fields)
            TestCase("GET", "User", "", "filter=networth:gte:1000,networth:lt:100000", "Filter networth range", 200),
            TestCase("GET", "User", "", "filter=dob:gte:1985-01-01,dob:lt:1995-12-31", "Filter date range", 200),
            TestCase("GET", "User", "", "filter=networth:gte:1000,dob:lt:2000-01-01", "Filter networth and date", 200),
            
            # Test field values in filtering
            TestCase("GET", "User", "", "filter=gender:female", "Filter with lowercase value", 200),
            TestCase("GET", "User", "", "filter=email:test@example.com", "Filter email with lowercase", 200),
            
            # Test mixed case URLs (server should convert to lowercase)
            TestCase("GET", "User", "", "Page=1&Page_Size=5", "Mixed case Page and Page_Size", 200),
            TestCase("GET", "User", "", "PAGE=2&page_SIZE=10", "Uppercase PAGE and mixed page_SIZE", 200),
            TestCase("GET", "User", "", "Sort=firstName&Filter=gender:female", "Mixed case Sort and Filter", 200),
            TestCase("GET", "User", "", "SORT=lastName,-createdAt&FILTER=networth:gte:1000", "Uppercase SORT and FILTER", 200),
            TestCase("GET", "User", "", "Page=1&Page_Size=3&Sort=netWorth&Filter=gender:female", "All mixed case parameters", 200),
            
            # Test complex combinations
            TestCase("GET", "User", "", "page=1&page_size=5&sort=firstname&filter=gender:female", "Combined parameters", 200),
            TestCase("GET", "User", "", "sort=lastname,-dob&filter=isaccountowner:true,gender:female", "Complex combination", 200),
            TestCase("GET", "User", "", "page=2&page_size=10&sort=networth&filter=dob:gte:1990-01-01", "Complex pagination with ranges", 200),
            
            # Test invalid field names (should generate application errors)
            # Todo: remove expected_response for bad fields - handled by generate_expected_response
            TestCase("GET", "User", "", "sort=invalidField", "Sort by invalid field name", 200, 
                expected_response={
                    "notifications": {
                        "errors": [{"type": "application", "message": "Sort criteria field 'invalidField' does not exist in entity"}]
                    }
                }),
            TestCase("GET", "User", "", "sort=firstname,badField", "Sort by valid and invalid fields", 200,
                expected_response={
                    "notifications": {
                        "errors": [{"type": "application", "message": "Sort criteria field 'badField' does not exist in entity"}]
                    }
                }),
            TestCase("GET", "User", "", "filter=nonExistentField:test", "Filter by invalid field name", 200,
                expected_response={
                    "notifications": {
                        "errors": [{"type": "application", "message": "Filter criteria field 'nonExistentField' does not exist in entity"}]
                    }
                }),
            TestCase("GET", "User", "", "filter=gender:male,invalidField:value", "Filter by valid and invalid fields", 200,
                expected_response={
                    "notifications": {
                        "errors": [{"type": "application", "message": "Filter criteria field 'invalidField' does not exist in entity"}]
                    }
                }),
            TestCase("GET", "User", "", "sort=badSort&filter=badFilter:value", "Sort and filter with invalid fields", 200,
                expected_response={
                    "notifications": {
                        "errors": [
                            {"type": "application", "message": "Sort criteria field 'badSort' does not exist in entity"},
                            {"type": "application", "message": "Filter criteria field 'badFilter' does not exist in entity"}
                        ]
                    }
                }),
            TestCase("GET", "User", "", "sort=firstName,invalidField&filter=gender:female,badField:test", "Mixed valid and invalid sort/filter", 200,
                expected_response={
                    "notifications": {
                        "errors": [
                            {"type": "application", "message": "Sort criteria field 'invalidField' does not exist in entity"},
                            {"type": "application", "message": "Filter criteria field 'badField' does not exist in entity"}
                        ]
                    }
                }),
        ]