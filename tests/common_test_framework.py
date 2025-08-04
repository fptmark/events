#!/usr/bin/env python3
"""
Common test framework for all API tests.
Provides shared utilities to eliminate code duplication.
"""

import json
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import quote

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import BaseTestFramework
from tests.data_validation_helper import DataValidationHelper

class CommonTestFramework(BaseTestFramework):
    """Extended test framework with common utilities for all test files"""
    
    def __init__(self, config_file: str, server_url: str = "http://127.0.0.1:5500", 
                 verbose: bool = False, curl_file_handle = None, mode_name: str = "",
                 request_delay: float = 0.1, curl_responses: Dict = None, json_output: bool = False):
        super().__init__(config_file, server_url, verbose, curl_file_handle, request_delay, curl_responses)
        self.curl_file_handle = curl_file_handle
        self.mode_name = mode_name
        self.test_results = []
        self.test_counter = 0
        self.passed_counter = 0
        self.json_output = json_output
        
        # Initialize data validation helper with User model
        try:
            from app.models.user_model import User
            self.data_validator = DataValidationHelper(User)
        except ImportError:
            self.data_validator = None
            if verbose:
                print("⚠️ Warning: Could not initialize data validator")
    
    def write_curl_commands_for_test_suite(self, test_suite_name: str, test_urls=None):
        """
        Pre-write all curl commands for a test suite.
        If test_urls is provided, use those. Otherwise, try to get URLs from get_test_urls() method.
        """
        if not self.curl_file_handle:
            return
        
        # Get URLs - either from parameter or from get_test_urls method
        if test_urls is None:
            if hasattr(self, 'get_test_urls'):
                test_urls = self.get_test_urls()
            else:
                if self.verbose:
                    print(f"⚠️ Warning: {self.__class__.__name__} doesn't define get_test_urls() method and no test_urls provided")
                return
            
        try:
            f = self.curl_file_handle
            f.write(f'# ========== {test_suite_name} ({self.mode_name}) ==========\n')
            
            for method, url, description in test_urls:
                full_url = f"{self.server_url}{url}"
                decoded_url = self._get_decoded_url_for_display(full_url)
                
                f.write(f'# {description}\n')
                f.write(f'echo "=== {method} {decoded_url} ==="\n')
                
                # Generate curl commands that output both JSON response and HTTP status
                if method.upper() == "GET":
                    f.write(f'response=$(curl -s -w "\\n%{{http_code}}" "{full_url}")\n')
                elif method.upper() in ["POST", "PUT"]:
                    f.write(f'response=$(curl -s -w "\\n%{{http_code}}" -X {method.upper()} "{full_url}")\n')
                elif method.upper() == "DELETE":
                    f.write(f'response=$(curl -s -w "\\n%{{http_code}}" -X DELETE "{full_url}")\n')
                
                # Split response body from status code and output both
                f.write('body=$(echo "$response" | head -n -1)\n')
                f.write('status=$(echo "$response" | tail -n 1)\n')
                
                if self.json_output:
                    # Output structured JSON format
                    f.write(f'echo "{{\\\"method\\\":\\\"{method}\\\",\\\"url\\\":\\\"{full_url}\\\",\\\"status\\\":$status,\\\"body\\\":$body}}"\n')
                else:
                    # Output original format
                    f.write('echo "$body"\n')
                    f.write(f'echo "CURL_RESULT|STATUS:$status|TIME:0|URL:{full_url}"\n')
                
                f.write('echo "CURL_END"\n\n')
                
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Warning: Could not write curl commands to file: {e}")
        
    def test_api_call(self, method: str, url: str, description: str, 
                     expected_notifications: List[str] = None,
                     expected_status: int = 200,
                     should_have_data: bool = True) -> bool:
        """
        Make API call and validate response with common logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            description: Test description for logging
            expected_notifications: List of field names that should have validation notifications
            expected_status: Expected HTTP status code
            should_have_data: Whether response should contain data
            
        Returns:
            True if test passes, False otherwise
        """
        if self.verbose:
            print(f"  🧪 {description}")
            print(f"      URL: {url}")
        
        # Make API request (delay is handled in BaseTestFramework.make_api_request)
        success, response = self.make_api_request(method, url, expected_status=expected_status)
        
        if not success:
            self.test_counter += 1
            if self.verbose:
                print(f"      ❌ API request failed")
                print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
            else:
                print(f"  📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
            return False
            
        # Skip data validation in curl generation mode
        if response.get("curl_generation_mode"):
            self.test_counter += 1
            self.passed_counter += 1
            if self.verbose:
                print(f"      ✅ {description} - CURL GENERATED")
                print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
            return True
            
        # Validate data presence
        if should_have_data:
            data = self.get_data(response)
            if not data or (isinstance(data, list) and len(data) == 0):
                self.test_counter += 1
                if self.verbose:
                    print(f"      ❌ Expected data but got empty response")
                    print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                else:
                    print(f"  📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                return False
        
        # Validate notifications if expected
        if expected_notifications:
            found_notifications = self._extract_notification_fields(response)
            missing = set(expected_notifications) - set(found_notifications)
            if missing:
                self.test_counter += 1
                if self.verbose:
                    print(f"      ❌ Missing expected notifications: {list(missing)}")
                    print(f"      📋 Found notifications: {found_notifications}")
                    print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                else:
                    print(f"  📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                return False
            if self.verbose:
                print(f"      ✅ Found expected notifications: {found_notifications}")
        
        # Validate pagination if present
        if 'pagination' in response:
            if not self._validate_pagination_structure(response['pagination']):
                self.test_counter += 1
                if self.verbose:
                    print(f"      ❌ Invalid pagination structure")
                    print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                else:
                    print(f"  📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                return False
                
        # Update counters and show progress
        self.test_counter += 1
        self.passed_counter += 1
        
        if self.verbose:
            print(f"      ✅ {description} - PASS")
            print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
        else:
            # Show progress even in non-verbose mode
            print(f"  📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
            
        return True
    
    def get_data(self, response: Dict[str, Any]) -> Any:
        """Extract data section from API response"""
        return response.get('data')
    
    def get_notifications(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract notifications section from API response"""
        return response.get('notifications', {})
    
    def get_status(self, response: Dict[str, Any]) -> str:
        """Extract status from API response"""
        return response.get('status', 'unknown')
    
    def get_summary(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract summary section from API response"""
        return response.get('summary', {})
    
    def get_pagination(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pagination section from API response"""
        return response.get('pagination', {})
    
    def _extract_notification_fields(self, response: Dict[str, Any]) -> List[str]:
        """Extract field names that have validation notifications"""
        fields = []
        notifications = self.get_notifications(response)
        
        for entity_id, entity_data in notifications.items():
            if isinstance(entity_data, dict):
                errors = entity_data.get('errors', [])
                warnings = entity_data.get('warnings', [])
                
                for item in errors + warnings:
                    if isinstance(item, dict) and item.get('type') == 'validation':
                        field_name = item.get('field')  # Fixed: use 'field' not 'field_name'
                        if field_name and field_name not in fields:
                            fields.append(field_name)
        
        return fields
    
    def _validate_pagination_structure(self, pagination: Dict[str, Any]) -> bool:
        """Validate pagination object has required GitHub-style fields"""
        required_fields = ['page', 'per_page', 'total', 'total_pages', 'has_next', 'has_prev']
        
        for field in required_fields:
            if field not in pagination:
                return False
                
        # Validate types
        if not isinstance(pagination.get('page'), int):
            return False
        if not isinstance(pagination.get('per_page'), int):
            return False
        if not isinstance(pagination.get('total'), int):
            return False
        if not isinstance(pagination.get('total_pages'), int):
            return False
        if not isinstance(pagination.get('has_next'), bool):
            return False
        if not isinstance(pagination.get('has_prev'), bool):
            return False
            
        return True
    
    def run_test_across_modes(self, test_function, test_name: str) -> Dict[str, bool]:
        """
        Run a test function across all 4 modes.
        
        Args:
            test_function: Function that runs the actual tests
            test_name: Name of the test for reporting
            
        Returns:
            Dict mapping mode names to success status
        """
        modes = [
            ("MongoDB_FK_ON", "mongo_fk_on.json"),
            ("MongoDB_FK_OFF", "mongo_fk_off.json"), 
            ("Elasticsearch_FK_ON", "es_fk_on.json"),
            ("Elasticsearch_FK_OFF", "es_fk_off.json")
        ]
        
        results = {}
        
        for mode_name, config_file in modes:
            if self.verbose:
                print(f"\n🔧 Testing {test_name} - {mode_name}")
                print("-" * 50)
                
            self.mode_name = mode_name
            
            try:
                # Update config file
                self.config_file = config_file
                
                # Run the test function
                success = test_function()
                results[mode_name] = success
                
                if self.verbose:
                    status = "✅ PASS" if success else "❌ FAIL"
                    print(f"  {status} - {test_name} ({mode_name})")
                    
            except Exception as e:
                results[mode_name] = False
                if self.verbose:
                    print(f"  ❌ FAIL - {test_name} ({mode_name}): {str(e)}")
        
        return results
    
    def test_api_call_with_validation(self, method: str, url: str, description: str,
                                    expected_notifications: List[str] = None,
                                    expected_status: int = 200,
                                    should_have_data: bool = True,
                                    validate_sort: List[tuple] = None,
                                    validate_filter: Dict[str, str] = None) -> bool:
        """
        Enhanced test_api_call that includes data validation for sorting and filtering.
        
        Args:
            validate_sort: List of (field_name, order) tuples e.g. [('firstName', 'asc')]
            validate_filter: Dict of field:value filters e.g. {'gender': 'male'}
        """
        if self.verbose:
            print(f"  🧪 {description}")
            print(f"      URL: {url}")
        
        # Make API request once (delay is handled in BaseTestFramework.make_api_request)
        api_success, response = self.make_api_request(method, url, expected_status=expected_status)
        if not api_success:
            self.test_counter += 1
            if self.verbose:
                print(f"      ❌ API request failed")
                print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
            return False
        
        # Skip data validation in curl generation mode
        if response.get("curl_generation_mode"):
            self.test_counter += 1
            self.passed_counter += 1
            if self.verbose:
                print(f"      ✅ {description} - CURL GENERATED")
                print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
            return True
        
        # Validate data presence
        if should_have_data:
            data = self.get_data(response)
            if not data or (isinstance(data, list) and len(data) == 0):
                self.test_counter += 1
                if self.verbose:
                    print(f"      ❌ Expected data but got empty response")
                    print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                return False
        
        # Validate notifications if expected
        if expected_notifications:
            found_notifications = self._extract_notification_fields(response)
            missing = set(expected_notifications) - set(found_notifications)
            if missing:
                self.test_counter += 1
                if self.verbose:
                    print(f"      ❌ Missing expected notifications: {list(missing)}")
                    print(f"      📋 Found notifications: {found_notifications}")
                    print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                return False
            if self.verbose:
                print(f"      ✅ Found expected notifications: {found_notifications}")
        
        # Validate pagination if present
        if 'pagination' in response:
            if not self._validate_pagination_structure(response['pagination']):
                self.test_counter += 1
                if self.verbose:
                    print(f"      ❌ Invalid pagination structure")
                    print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                return False
            
        # Get data for validation
        data = self.get_data(response)
        
        # Skip data validation if no list data or no validator
        if not self.data_validator or not data or not isinstance(data, list):
            if self.verbose and (validate_sort or validate_filter):
                print(f"      ⚠️ Skipping data validation - no list data found or no validator")
            # Mark test as passed for standard validations
            self.test_counter += 1
            self.passed_counter += 1
            if self.verbose:
                print(f"      ✅ {description} - PASS")
                print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
            return True
        
        # Validate sorting if requested
        if validate_sort:
            sort_valid, sort_msg = self.data_validator.validate_sort_order(data, validate_sort)
            if not sort_valid:
                if self.verbose:
                    print(f"      ❌ Sort validation failed: {sort_msg}")
                return False
            elif self.verbose:
                print(f"      ✅ Sort validation passed: {sort_msg}")
        
        # Validate filtering if requested  
        if validate_filter:
            filter_valid, filter_msg = self.data_validator.validate_filter_results(data, validate_filter)
            if not filter_valid:
                if self.verbose:
                    print(f"      ❌ Filter validation failed: {filter_msg}")
                return False
            elif self.verbose:
                print(f"      ✅ Filter validation passed: {filter_msg}")
        
        # Validate combined sort+filter if both requested
        if validate_sort and validate_filter:
            combined_valid, combined_msg = self.data_validator.validate_combined_sort_filter(
                data, validate_sort, validate_filter)
            if not combined_valid:
                self.test_counter += 1
                if self.verbose:
                    print(f"      ❌ Combined validation failed: {combined_msg}")
                    print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
                return False
            elif self.verbose:
                print(f"      ✅ Combined validation passed: {combined_msg}")
        
        # All validations passed
        self.test_counter += 1
        self.passed_counter += 1
        if self.verbose:
            print(f"      ✅ {description} - PASS")
            print(f"      📊 Progress: {self.passed_counter}/{self.test_counter} tests passed")
        
        return True
    
    
    def summary_report(self, test_name: str, results: Dict[str, bool]) -> bool:
        """Generate summary report for a test across all modes"""
        total_modes = len(results)
        passed_modes = sum(1 for success in results.values() if success)
        
        print(f"\n📊 {test_name} Summary:")
        print(f"  Modes passed: {passed_modes}/{total_modes}")
        
        for mode, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {mode}")
        
        overall_success = passed_modes == total_modes
        if overall_success:
            print(f"  🎉 {test_name} - ALL MODES PASSED")
        else:
            print(f"  🚨 {test_name} - {total_modes - passed_modes} MODE(S) FAILED")
            
        return overall_success

# Test data constants
TEST_USERS = {
    "valid_all": "valid_all_user_123456",
    "valid_fk_only": "valid_fk_only_user_123456", 
    "bad_enum": "bad_enum_user_123456",
    "bad_currency": "bad_currency_user_123456",
    "bad_fk": "bad_fk_user_123456",
    "multiple_errors": "multiple_errors_user_123456",
    "nonexistent": "nonexistent_user_123456"
}

TEST_ACCOUNTS = {
    "primary": "primary_account_123456",
    "secondary": "secondary_account_123456"
}