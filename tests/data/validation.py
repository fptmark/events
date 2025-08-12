"""
Clean Validation System - Simple, focused validation logic.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import re
from urllib.parse import urlparse, parse_qs

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import utils


class Validator:
    """
    Clean validation system - validates actual API responses against TestCase expectations.
    """
    
    def __init__(self, test_case, result: Dict, config: Dict, verbose: bool = False):
        self.test_case = test_case
        self.result = result
        self.config = config
        self.verbose = verbose
        
        # Get model metadata once
        model_class = utils.get_model_class(test_case.entity)
        self.metadata = model_class.get_metadata()
        self.fields = self.metadata.get('fields', {})
        
        # Determine request type
        self.is_single_request = bool(test_case.id)
        self.fk_validation_enabled = self.config.get('fk_validation', '') in ['single', 'multiple']
        
    def validate_test_case(self) -> bool:
        """Main validation entry point"""
        # Basic structure validation (required for all responses)
        if not self._validate_basic_structure():
            return False
            
        # Single entity validation (comprehensive)
        if self.is_single_request:
            return self._validate_single_entity()
            
        # List validation (pagination, sorting, filtering)
        return self._validate_list_response()
    
    # ==================== BASIC STRUCTURE VALIDATION ====================
    
    def _validate_basic_structure(self) -> bool:
        """Validate basic response structure - applies to all responses"""
        # Must have data field
        if 'data' not in self.result:
            print(f"    ❌ Missing 'data' field in response")
            return False
        
        data = self.result['data']
        
        # Single request = single object, List request = array
        if self.is_single_request:
            if isinstance(data, list):
                print(f"    ❌ Single entity request returned array, expected object")
                return False
        else:
            if not isinstance(data, list):
                print(f"    ❌ List request returned object, expected array")
                return False
                
        # Validate notifications structure if expected
        if self.test_case.expected_response and 'notifications' in self.test_case.expected_response:
            if not self._validate_notification_counts():
                return False
                
        return True
    
    def _validate_notification_counts(self) -> bool:
        """Validate notification count matches expectation for both single and multiple results"""
        expected_notifications = self.test_case.expected_response.get('notifications', {})
        for entity_id, entity_data in expected_notifications.items():
            expected_warnings = entity_data.get('warnings', [])
            result_warnings = self.result['notifications'].get(entity_id, {}).get('warnings', [])
            if len(expected_warnings) != len(result_warnings):
                print(f"    ❌ Warnings count mismatch")
                return False

        return True 
    
    def _validate_single_entity(self) -> bool:
        """Comprehensive validation for single entity responses"""
        
        # Expected response validation (deep field comparison)
        if self.test_case.expected_response:
            if not self._validate_expected_response(self.result):
                return False
        
        # FK sub-object validation
        if self.fk_validation_enabled or self.test_case.expected_sub_objects:
            if not self._validate_fk_sub_objects(self.result['data']):
                return False
                
        return True
    
    def _validate_expected_response(self, actual_response: Dict) -> bool:
        """Validate actual data matches expected_response exactly"""
        expected_data = self.test_case.expected_response.get('data', {})
        actual_data = actual_response.get('data', {})

        # Check that auto fields exist in the actual data
        for field_name, field_info in self.fields.items():
            if field_info.get('autoGenerate') or field_info.get('autoUpdate'):
                if field_name not in actual_data or not actual_data[field_name]:
                    if self.verbose:
                        print(f"    ❌ Missing auto-generated field or contents '{field_name}' in actual data")
                    return False
        
        # Remove auto-generated fields and None optional fields from comparison
        cleaned_actual = self._remove_fields(actual_data.copy(), self.metadata)
        cleaned_expected = self._remove_fields(expected_data.copy(), self.metadata)
        
        # Compare data fields
        if not self._compare_objects(cleaned_actual, cleaned_expected, "data"):
            return False
            
        # Compare warnings if specified
        expected_warnings = self.test_case.expected_response.get('notifications', []).get(self.test_case.id, {}).get('warnings', [])
        if expected_warnings:
            actual_warnings = actual_response.get('notifications', []).get(self.test_case.id, {}).get('warnings', [])
            if not self._compare_warnings(actual_warnings, expected_warnings):
                return False
                
        return True
    
    def _validate_fk_sub_objects(self, data: Dict) -> bool:
        """Validate FK sub-objects are properly populated"""
        # Find FK fields in the data
        for field_name, field_value in data.items():
            fk_entity = utils.get_fk_entity(field_name)
            if fk_entity:
                
                # Check if sub-object exists
                if fk_entity not in data:
                    if self.verbose:
                        print(f"    ❌ Missing FK sub-object '{fk_entity}' for field '{field_name}'")
                    return False
                    
                sub_object = data[fk_entity]
                if not isinstance(sub_object, dict) or 'exists' not in sub_object:
                    if self.verbose:
                        print(f"    ❌ Invalid FK sub-object structure for '{fk_entity}'")
                    return False
                    
                # Validate expected fields in sub-object
                if self.test_case.expected_sub_objects:
                    expected_fields = self._get_expected_fields_for_entity(fk_entity)
                    if expected_fields and sub_object.get('exists'):
                        for field in expected_fields:
                            if field not in sub_object:
                                if self.verbose:
                                    print(f"    ❌ Missing expected field '{field}' in FK sub-object '{fk_entity}'")
                                return False
                                
        return True
    
    # ==================== LIST RESPONSE VALIDATION ====================
    
    def _validate_list_response(self) -> bool:
        """Validate list responses (pagination, sorting, filtering)"""
        data = self.result['data']
        
        # Pagination validation (required for list responses)
        if not self._validate_pagination():
            return False
            
        # Sort validation
        if self.test_case.expected_sort:
            if not self._validate_sort_order(data):
                return False
                
        # Filter validation  
        if self.test_case.expected_filter:
            if not self._validate_filtering(data):
                return False
                
        return True
    
    def _validate_pagination(self) -> bool:
        """Validate pagination structure"""
        if 'pagination' not in self.result:
            if self.verbose:
                print(f"    ❌ Missing pagination object in list response")
            return False
            
        pagination = self.result['pagination']
        required_fields = ['page', 'per_page', 'total', 'total_pages', 'has_next', 'has_prev']
        
        # Check required fields
        for field in required_fields:
            if field not in pagination:
                if self.verbose:
                    print(f"    ❌ Missing pagination field '{field}'")
                return False
                
        # Validate field types
        page = pagination['page']
        per_page = pagination['per_page'] 
        total = pagination['total']
        total_pages = pagination['total_pages']
        has_next = pagination['has_next']
        has_prev = pagination['has_prev']
        
        if not (isinstance(page, int) and page >= 1):
            if self.verbose:
                print(f"    ❌ Invalid page: {page} (must be int >= 1)")
            return False
            
        if not (isinstance(per_page, int) and per_page >= 1):
            if self.verbose:
                print(f"    ❌ Invalid per_page: {per_page} (must be int >= 1)")
            return False
            
        if not (isinstance(total, int) and total >= 0):
            if self.verbose:
                print(f"    ❌ Invalid total: {total} (must be int >= 0)")
            return False
            
        if not (isinstance(total_pages, int) and total_pages >= 0):
            if self.verbose:
                print(f"    ❌ Invalid total_pages: {total_pages} (must be int >= 0)")
            return False
            
        if not isinstance(has_next, bool):
            if self.verbose:
                print(f"    ❌ Invalid has_next: {has_next} (must be boolean)")
            return False
            
        if not isinstance(has_prev, bool):
            if self.verbose:
                print(f"    ❌ Invalid has_prev: {has_prev} (must be boolean)")
            return False
            
        # Validate pagination logic
        if has_prev != (page > 1):
            if self.verbose:
                print(f"    ❌ Pagination logic error: has_prev={has_prev} but page={page}")
            return False
            
        if has_next != (page < total_pages):
            if self.verbose:
                print(f"    ❌ Pagination logic error: has_next={has_next} but page={page} of {total_pages}")
            return False
            
        return True
    
    def _validate_sort_order(self, data: List[Dict]) -> bool:
        """Validate data is sorted according to expected_sort"""
        if len(data) < 2:
            return True  # Can't validate sort with < 2 items
            
        expected_sort = self.test_case.expected_sort
        
        for i in range(len(data) - 1):
            current = data[i]
            next_item = data[i + 1]
            
            # Check sort order for each field in sequence
            for field_name, direction in expected_sort:
                current_val = current.get(field_name)
                next_val = next_item.get(field_name)
                
                # Compare values using metadata-aware comparison
                comparison = self._compare_values(current_val, next_val, field_name)
                
                if comparison == 0:
                    continue  # Equal, check next sort field
                    
                # Check if order is correct
                if direction == 'asc' and comparison > 0:
                    if self.verbose:
                        print(f"    ❌ Sort order violation: '{current_val}' should come after '{next_val}' for field '{field_name}' (asc)")
                    return False
                elif direction == 'desc' and comparison < 0:
                    if self.verbose:
                        print(f"    ❌ Sort order violation: '{current_val}' should come before '{next_val}' for field '{field_name}' (desc)")
                    return False
                else:
                    break  # Correct order, move to next pair
                    
        return True
    
    def _validate_filtering(self, data: List[Dict]) -> bool:
        """Validate all data items match filter criteria"""
        expected_filter = self.test_case.expected_filter
        
        for i, record in enumerate(data):
            for field_name, expected_value in expected_filter.items():
                actual_value = record.get(field_name)
                expected_typed = self._convert_filter_value(field_name, expected_value)
                
                if actual_value != expected_typed:
                    if self.verbose:
                        print(f"    ❌ Filter mismatch: Record {i} has {field_name}='{actual_value}', expected '{expected_typed}'")
                    return False
                    
        return True
    
    # ==================== HELPER METHODS ====================
    
    def _remove_fields(self, data: Dict, metadata: Dict) -> Dict:
        """Remove auto-generated fields, None optional fields, and ignore_fields using metadata"""
        cleaned = data.copy()
        fields = metadata.get('fields', {})
        
        for field_name, field_info in fields.items():
            # Remove auto-generated/auto-updated fields
            if field_info.get('autoGenerate') or field_info.get('autoUpdate'):
                cleaned.pop(field_name, None)
                continue
                
            # Remove optional fields that are None
            if not field_info.get('required', False):
                if cleaned.get(field_name) is None:
                    cleaned.pop(field_name, None)
                    
        # All field removal now handled by metadata - no special ignore_fields needed
        
        return cleaned
    
    def _compare_objects(self, actual: Dict, expected: Dict, path: str) -> bool:
        """Compare two objects field by field"""
        # Check all expected fields are present
        for field_name, expected_value in expected.items():
            if field_name not in actual:
                if self.verbose:
                    print(f"    ❌ Missing expected field '{field_name}' in {path}")
                return False
                
            actual_value = actual[field_name]
            field_path = f"{path}.{field_name}"
            
            # Recursive comparison for nested objects
            if isinstance(expected_value, dict) and isinstance(actual_value, dict):
                if not self._compare_objects(actual_value, expected_value, field_path):
                    return False
            elif isinstance(expected_value, list) and isinstance(actual_value, list):
                if not self._compare_arrays(actual_value, expected_value, field_path):
                    return False
            else:
                # Direct value comparison
                if actual_value != expected_value:
                    if self.verbose:
                        print(f"    ❌ Value mismatch at {field_path}: expected '{expected_value}', got '{actual_value}'")
                    return False
                    
        return True
    
    def _compare_arrays(self, actual: List, expected: List, path: str) -> bool:
        """Compare two arrays"""
        if len(actual) != len(expected):
            if self.verbose:
                print(f"    ❌ Array length mismatch at {path}: expected {len(expected)}, got {len(actual)}")
            return False
            
        for i, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            item_path = f"{path}[{i}]"
            if isinstance(expected_item, dict) and isinstance(actual_item, dict):
                if not self._compare_objects(actual_item, expected_item, item_path):
                    return False
            elif actual_item != expected_item:
                if self.verbose:
                    print(f"    ❌ Array item mismatch at {item_path}: expected '{expected_item}', got '{actual_item}'")
                return False
                
        return True
    
    def _compare_warnings(self, actual_warnings: List, expected_warnings: List) -> bool:
        """Compare warning arrays"""
        if len(actual_warnings) != len(expected_warnings):
            if self.verbose:
                print(f"    ❌ Warning count mismatch: expected {len(expected_warnings)}, got {len(actual_warnings)}")
            return False
            
        # For warnings, we mainly care about field names and types, not exact messages
        actual_fields = {w.get('field') for w in actual_warnings}
        expected_fields = {w.get('field') for w in expected_warnings}
        
        if actual_fields != expected_fields:
            if self.verbose:
                print(f"    ❌ Warning fields mismatch: expected {expected_fields}, got {actual_fields}")
            return False
            
        return True
    
    def _extract_warnings_for_entity(self, entity_id: str) -> List[Dict]:
        """Extract warnings for specific entity from notifications"""
        notifications = self.result.get('notifications', {})
        entity_notifications = notifications.get(entity_id, {})
        return entity_notifications.get('warnings', [])
    
    def _get_expected_fields_for_entity(self, entity_name: str) -> List[str]:
        """Get expected fields for FK entity from expected_sub_objects"""
        if not self.test_case.expected_sub_objects:
            return []
            
        for sub_obj_spec in self.test_case.expected_sub_objects:
            if entity_name in sub_obj_spec:
                return sub_obj_spec[entity_name]
                
        return []
    
    def _compare_values(self, val1: Any, val2: Any, field_name: str) -> int:
        """Compare two values using metadata-aware type handling. Returns -1, 0, or 1"""
        field_info = self.fields.get(field_name, {})
        field_type = field_info.get('type', 'String')
        
        # Handle None values
        if val1 is None and val2 is None:
            return 0
        elif val1 is None:
            return -1  # None comes first
        elif val2 is None:
            return 1
            
        # Type-specific comparisons
        if field_type in ['Integer', 'Currency', 'Float']:
            num1, num2 = float(val1), float(val2)
            return -1 if num1 < num2 else (1 if num1 > num2 else 0)
        elif field_type in ['Date', 'Datetime']:
            try:
                if isinstance(val1, datetime) and isinstance(val2, datetime):
                    return -1 if val1 < val2 else (1 if val1 > val2 else 0)
                # Try parsing ISO format
                date1 = datetime.fromisoformat(str(val1).replace('Z', '+00:00'))
                date2 = datetime.fromisoformat(str(val2).replace('Z', '+00:00'))
                return -1 if date1 < date2 else (1 if date1 > date2 else 0)
            except:
                pass  # Fall through to string comparison
        elif field_type == 'Boolean':
            bool1, bool2 = bool(val1), bool(val2)
            return -1 if bool1 < bool2 else (1 if bool1 > bool2 else 0)
            
        # Default: case-insensitive string comparison
        str1 = str(val1).lower()
        str2 = str(val2).lower()
        return -1 if str1 < str2 else (1 if str1 > str2 else 0)
    
    def _convert_filter_value(self, field_name: str, filter_value: str) -> Any:
        """Convert string filter value to proper type using metadata"""
        field_info = self.fields.get(field_name, {})
        field_type = field_info.get('type', 'String')
        
        if field_type == 'Boolean':
            return filter_value.lower() in ['true', '1', 'yes']
        elif field_type == 'Integer':
            return int(filter_value)
        elif field_type in ['Currency', 'Float']:
            return float(filter_value)
        else:
            return filter_value  # String or other types