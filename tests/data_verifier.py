#!/usr/bin/env python3
"""
Data Verifier for Test Framework

Unified data verification combining the best from DataValidationHelper 
and CT verification functions. Handles all TestCase validation needs.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
import re
from urllib.parse import urlparse, parse_qs
from base_test import TestCase
from utils import get_model_class

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class DataVerifier():
    def __init__(self, test_case: TestCase, result, config: Dict, verbose: bool):
        self.test_case = test_case
        self.result = result
        self.config = config
        self.verbose = verbose

        model_class = get_model_class(test_case.entity)
        self.metadata = model_class.get_metadata()
        self.fields = self.metadata.get('fields', {})
        self.expected_response = test_case.generate_expected_response()
        self.fk_validation_setting = self.config.get('fk_validation', '')
        self.view_objects = self._parse_view_parameters(self.test_case.url)

    # Todo: get fk_validation from config as it may change the results
    def verify_test_case(self) -> bool:
        """Main entry point - verify all TestCase expectations"""
        if not self.test_case.id:
            if self.verbose:
                print("    No validation of mutliple response calls")
            return True

        # Auto-populate expected sub-objects from view parameters if not already set
        if self.test_case.expected_sub_objects is None and self.view_objects:
            self.test_case.expected_sub_objects = [self.view_objects]
        
        # fk validation is on if =multiple as this is expensive.  only check single response if fk_validation is set to single
        fk_validation: bool = (self.fk_validation_setting == 'multiple') or (self.fk_validation_setting == 'single' and self.test_case.is_single())
        
        # Make sure result is a List for multiple responses or a Dict for single response
        if not (self.test_case.is_single() ^ isinstance(self.result['data'], list)):
            return False  # Inconsistent response type

        # Build dynamic ignore list from autogen/autoupdate fields + custom ignore_fields
        ignore_fields = self._build_ignore_fields_list(self.expected_response)
        
        # Remove fields using the dynamic ignore_list
        if self.expected_response and ignore_fields:
            for field in ignore_fields:
                self.expected_response.get('data', {}).pop(field, None)
                if isinstance(self.result['data'], dict):
                    self.result['data'].pop(field, None)
                elif isinstance(self.result['data'], list) and self.result['data']:
                    for item in self.result['data']:
                        item.pop(field, None)

        # Surface-level validation
        if not self._verify_data_structure(self.test_case, self.result, fk_validation, self.view_objects):
            return False
        
        # Deep validation for fixed records
        if not self._verify_deep_response(self.test_case, self.result):
            return False
            
        # verify sub-objects.  they will exist based on the view param and the fk_validation setting
        if not self._validate_sub_objects(self.test_case, self.result, fk_validation, self.view_objects):
            return False

        # Sort order validation
        if not self._verify_sort_order(self.test_case, self.result):
            return False
            
        # Filter criteria validation
        if not self._verify_filtering(self.test_case, self.result):
            return False
            
        return True

    def _validate_sub_objects(self, test_case, results, fk_validation: bool, view_objects: Dict) -> bool:
        """Validate sub-objects based on expected_sub_objects array and view parameters"""
        # Use expected_sub_objects if available, otherwise fall back to view_objects
        expected_sub_objects = test_case.expected_sub_objects or ([view_objects] if view_objects else [])
        
        if expected_sub_objects or fk_validation:
            data_list = results.get('data', [])
            if not isinstance(data_list, list):
                data_list = [data_list]
                
            for result in data_list:
                id = result.get('id')
                for field in result:
                    # for objectId fields with no notifications, validate the sub-object if fk_validation is set or a view parameter exists
                    fk_entity_name = self._get_fk_entity_name(field)
                    if fk_entity_name and not self._get_notification(results.get('notifications', {}), field, id):
                        # Check if this entity is expected in any of the sub-object specs
                        expected_fields = []
                        for sub_obj_spec in expected_sub_objects:
                            if fk_entity_name in sub_obj_spec:
                                expected_fields = sub_obj_spec[fk_entity_name]
                                break
                        
                        if expected_fields or fk_validation:
                            subobj = result.get(fk_entity_name, {})
                            if not subobj:
                                if self.verbose:
                                    print(f"       ❌ Missing sub-object {fk_entity_name} for id {id}")
                                return False
                            if 'exists' not in subobj:
                                if self.verbose:
                                    print(f"       ❌ Missing 'exists' field in sub-object {fk_entity_name} for id {id}")
                                return False
                            
                            # Validate expected fields are present in sub-object
                            if expected_fields and subobj.get('exists'):
                                for field_name in expected_fields:
                                    if field_name not in subobj:
                                        if self.verbose:
                                            print(f"       ❌ Missing expected field '{field_name}' in sub-object {fk_entity_name} for id {id}")
                                        return False
        return True

    def _get_notification(self, notifications: dict, field: str, id: str) -> dict:
        entity_notifications = notifications.get(id, {})
        if entity_notifications:
            for warning in entity_notifications.get('warnings', []):
                if warning.get('field') == field:
                    return warning
        return {}

    def _compute_notification_count(self, expected_response: dict, fk_validation: bool, view_objects: Dict) -> int:
        """Compute expected notification count from expected_response structure"""
        warnings = expected_response.get('warnings', [])
        count = len(warnings)
        for warning in warnings:
            fk_entity_name = self._get_fk_entity_name(warning.get('field'))
            # fk warning exists. it does count if it's a non-existant message 
            if fk_entity_name and warning.get('message') != "Field required":
            # fk warning exists. it doesn't count if fk_validation is not set or view_objects does not have this fk_entity_name
                if not fk_validation or (not view_objects.get(fk_entity_name)):
                    count -= 1
        return count

    def _get_fk_entity_name(self, field: str) -> Optional[str]:
        """Extract FK entity name from field name"""
        if field.endswith('Id'):
            return field[:-2]
        return None

    def _verify_data_structure(self, test_case, result: dict, fk_validation: bool, view_objects: Dict   ) -> bool:
        """Verify basic data structure expectations"""
        is_single_response = self.expected_response is not None
        
        # For single response tests, compute expected lengths from expected_response
        if is_single_response:
            expected_data_len = len(test_case.expected_response.get('data', []))
            expected_notification_len = self._compute_notification_count(test_case.expected_response, fk_validation, view_objects)
        else:
            # For multi-response tests, use explicit values (if provided)
            expected_data_len = test_case.expected_data_len
            expected_notification_len = None
        
        # Check expected data length
        if expected_data_len is not None:
            if 'data' not in result:
                if self.verbose:
                    print(f"      ❌ Expected data field, but not found")
                return False
            # For expected_data_len, data should be an array
            data = result.get('data', {})
            if len(data) != expected_data_len:
                if self.verbose:
                    print(f"      ❌ Expected {expected_data_len} data items, got {len(data)}")
                return False
        
        # Check expected notification length
        if expected_notification_len is not None:
            notifications = result.get('notifications', {})
            
            if is_single_response:
                # For single response, get notifications for the single user
                # data_item = result['data'][0] if isinstance(result['data'], list) else result['data']
                id = data.get('id')
                notifications = notifications.get(id, {})
                warnings = notifications.get('warnings', [])
                notification_count = len(warnings)
            else:
                # For list response, count total notifications across all users
                notification_count = len(notifications)
            
            if notification_count != expected_notification_len:
                if self.verbose:
                    print(f"      ❌ Expected {expected_notification_len} notifications, got {notification_count}")
                return False
        
        # Check expected pagination
        if test_case.expected_paging and 'pagination' not in result:
            if self.verbose:
                print(f"      ❌ Expected pagination object, but not found")
            return False
            
        return True

    def _verify_deep_response(self, test_case, result) -> bool:
        """Deep validation for fixed records"""
        if self.expected_response is None:
            return True  # No deep validation required
        
        # Transform the expected structure to match API response format if needed
        expected_transformed = self._transform_expected_response(self.expected_response, result)
        return self._deep_validate(result, expected_transformed, "root")

    def _transform_expected_response(self, expected: dict, actual: dict) -> dict:
        """Transform simplified expected structure to match actual API response format"""
        transformed = expected.copy()
        
        # If expected has 'warnings' but actual has 'notifications', transform the structure
        if 'warnings' in expected and 'notifications' in actual:
            warnings = expected['warnings']
            # Get the user ID from the actual response data
            data_item = actual['data'][0] if isinstance(actual['data'], list) else actual['data']
            user_id = data_item.get('id')
            
            # Transform to nested notification structure
            transformed['notifications'] = {
                user_id: {
                    'warnings': warnings
                }
            }
            # Remove the flat warnings array
            del transformed['warnings']
        
        return transformed

    def _deep_validate(self, actual, expected, field_path: str = "root") -> bool:
        """Deep validation - recursively compare actual vs expected response"""
        if type(actual) != type(expected):
            if self.verbose:
                print(f"      ❌ Type mismatch at {field_path}: expected {type(expected).__name__}, got {type(actual).__name__}")
            return False
            
        if isinstance(expected, dict):
            for key, expected_value in expected.items():
                current_path = f"{field_path}.{key}" if field_path != "root" else key
                if key not in actual:
                    if self.verbose:
                        print(f"      ❌ Missing expected key at {current_path}")
                    return False
                
                # Special handling for message field - just check it's non-blank
                if key == "message":
                    actual_message = actual[key]
                    if not actual_message or str(actual_message).strip() == "":
                        if self.verbose:
                            print(f"      ❌ Empty message at {current_path}")
                        return False
                    # Don't validate exact message content - just that it exists and is non-blank
                    continue
                    
                if not self._deep_validate(actual[key], expected_value, current_path):
                    return False
        elif isinstance(expected, list):
            if len(actual) != len(expected):
                if self.verbose:
                    print(f"      ❌ Array length mismatch at {field_path}: expected {len(expected)}, got {len(actual)}")
                return False
            for i, expected_item in enumerate(expected):
                current_path = f"{field_path}[{i}]"
                if not self._deep_validate(actual[i], expected_item, current_path):
                    return False
        else:
            # Primitive values - direct comparison
            if actual != expected:
                if self.verbose:
                    print(f"      ❌ Value mismatch at {field_path}: expected '{expected}', got '{actual}'")
                return False
                
        return True

    def _verify_sort_order(self, test_case, result) -> bool:
        """Verify sort order using advanced type-aware comparison"""
        if test_case.expected_sort is None:
            return True  # No sort validation required
            
        if 'data' not in result:
            return True  # No data to sort
            
        data = result['data']
        if not isinstance(data, list):
            data = [data]  # Convert singleton to array
            
        if len(data) <= 1:
            return True  # Can't verify sort order with 0 or 1 items
            
        # Use advanced sort validation
        valid, error_msg = self._validate_sort_order_advanced(data, test_case.expected_sort)
        if not valid and self.verbose:
            print(f"      ❌ {error_msg}")
        return valid

    def _validate_sort_order_advanced(self, data: List[Dict], sort_fields: List[tuple]) -> tuple[bool, str]:
        """Advanced sort validation with type awareness and detailed error messages"""
        if len(data) < 2:
            return True, "Less than 2 records, sort validation skipped"
        
        for i in range(len(data) - 1):
            current = data[i]
            next_item = data[i + 1]
            
            # Check each sort field in order
            for field_name, order in sort_fields:
                current_val = current.get(field_name)
                next_val = next_item.get(field_name)
                
                # Handle None values - sort them to the end
                if current_val is None and next_val is None:
                    continue
                elif current_val is None:
                    if order == 'asc':
                        return False, f"Sort validation failed: None value should come after non-None for field '{field_name}' (asc order)"
                elif next_val is None:
                    if order == 'desc':
                        return False, f"Sort validation failed: None value should come after non-None for field '{field_name}' (desc order)"
                    continue  # None values go to end in asc order, this is correct
                
                # Compare non-None values using type-aware comparison
                try:
                    comparison = self._compare_values(current_val, next_val, field_name)
                    
                    if comparison == 0:
                        continue  # Equal values, check next sort field
                    elif order == 'asc' and comparison > 0:
                        return False, f"Sort validation failed: '{current_val}' should come after '{next_val}' for field '{field_name}' (asc order)"
                    elif order == 'desc' and comparison < 0:
                        return False, f"Sort validation failed: '{current_val}' should come before '{next_val}' for field '{field_name}' (desc order)"
                    else:
                        break  # Correct order found, no need to check remaining sort fields for this pair
                        
                except Exception as e:
                    return False, f"Sort validation error for field '{field_name}': {e}"
        
        return True, "Sort validation passed"

    def _verify_filtering(self, test_case, result) -> bool:
        """Verify filtering using advanced type-aware comparison"""
        if test_case.expected_filter is None:
            return True  # No filter validation required
            
        if 'data' not in result:
            return True  # No data to filter
            
        data = result['data']
        if not isinstance(data, list):
            data = [data]  # Convert singleton to array
            
        # Use advanced filter validation
        valid, error_msg = self._validate_filter_results_advanced(data, test_case.expected_filter)
        if not valid and self.verbose:
            print(f"      ❌ {error_msg}")
        return valid

    def _validate_filter_results_advanced(self, data: List[Dict], filter_criteria: Dict[str, str]) -> tuple[bool, str]:
        """Advanced filter validation with type awareness"""
        for i, record in enumerate(data):
            for field_name, expected_value in filter_criteria.items():
                actual_value = record.get(field_name)
                
                # Convert expected value to proper type for comparison
                try:
                    expected_typed = self._convert_filter_value(field_name, expected_value)
                    
                    if actual_value != expected_typed:
                        return False, f"Filter validation failed: Record {i} has {field_name}='{actual_value}', expected '{expected_typed}'"
                        
                except Exception as e:
                    return False, f"Filter validation error for field '{field_name}': {e}"
        
        return True, f"Filter validation passed for {len(data)} records"

    def _parse_view_parameters(self, url: str) -> Dict[str, List[str]]:
        """Parse view parameters from URL and return array of {'entity': [<fields>]}"""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            view_param = query_params.get('view', [])
            if not view_param:
                return {}
            
            view_data = json.loads(view_param[0])
            if isinstance(view_data, dict):
                entity = list(view_data.keys())[0]
                # Convert {'entity': ['field1', 'field2']} to [{'entity': ['field1', 'field2']}]
                return {entity: view_data[entity]}

        except Exception as e:
            print(f"      ⚠️  Failed to parse view parameters from URL {url}: {e}")
                
        return {}

    def _compare_values(self, val1: Any, val2: Any, field_name: str) -> int:
        """Type-aware value comparison. Returns: -1 if val1 < val2, 0 if equal, 1 if val1 > val2"""
        field_type = self._get_field_type(field_name)
        
        # Handle string comparisons (case-insensitive for consistency)
        if field_type in ['String']:
            str1 = str(val1).lower() if val1 is not None else ''
            str2 = str(val2).lower() if val2 is not None else ''
            if str1 < str2:
                return -1
            elif str1 > str2:
                return 1
            else:
                return 0
        
        # Handle numeric comparisons
        elif field_type in ['Integer', 'Currency', 'Float']:
            num1 = float(val1) if val1 is not None else 0
            num2 = float(val2) if val2 is not None else 0
            if num1 < num2:
                return -1
            elif num1 > num2:
                return 1
            else:
                return 0
        
        # Handle date comparisons
        elif field_type == 'Date':
            try:
                date1 = val1 if isinstance(val1, datetime) else datetime.fromisoformat(val1.replace('Z', '+00:00'))
                date2 = val2 if isinstance(val2, datetime) else datetime.fromisoformat(val2.replace('Z', '+00:00'))
                if date1 < date2:
                    return -1
                elif date1 > date2:
                    return 1
                else:
                    return 0
            except:
                # Fall back to string comparison if date parsing fails
                pass
        
        # Handle boolean comparisons  
        elif field_type == 'Boolean':
            bool1 = bool(val1) if val1 is not None else False
            bool2 = bool(val2) if val2 is not None else False
            if bool1 < bool2:
                return -1
            elif bool1 > bool2:
                return 1
            else:
                return 0
        
        # Default to case-insensitive string comparison
        str1 = str(val1).lower() if val1 is not None else ''
        str2 = str(val2).lower() if val2 is not None else ''
        
        if str1 < str2:
            return -1
        elif str1 > str2:
            return 1
        else:
            return 0

    def _convert_filter_value(self, field_name: str, filter_value: str) -> Any:
        """Convert string filter value to proper type for comparison"""
        field_type = self._get_field_type(field_name)
        
        if field_type == 'Boolean':
            return filter_value.lower() in ['true', '1', 'yes']
        elif field_type in ['Integer']:
            return int(filter_value)
        elif field_type in ['Currency', 'Float']:
            return float(filter_value)
        elif field_type == 'String':
            # Check if it's an enum field
            enum_values = self._get_enum_values(field_name)
            if enum_values and filter_value not in enum_values:
                raise ValueError(f"'{filter_value}' is not a valid enum value for {field_name}. Valid values: {enum_values}")
            return filter_value
        else:
            return filter_value  # Keep as string for other types

    def _get_field_type(self, field_name: str) -> Optional[str]:
        """Get the type of a field from metadata"""
        field_info = self.fields.get(field_name, {})
        return field_info.get('type')

    def _get_enum_values(self, field_name: str) -> Optional[List[str]]:
        """Get valid enum values for a field"""
        field_info = self.fields.get(field_name, {})
        enum_info = field_info.get('enum', {})
        return enum_info.get('values', []) if enum_info else None

    def _build_ignore_fields_list(self, expected_response: Optional[dict]) -> List[str]:
        """Build dynamic ignore list from autogen/autoupdate fields + custom ignore_fields"""
        ignore_fields = []
        
        # Add autogen and autoupdate fields from model metadata
        for field_name, field_info in self.fields.items():
            if field_info.get('autoGenerate') or field_info.get('autoUpdate'):
                ignore_fields.append(field_name)
        
        # Add custom ignore_fields if provided in expected_response
        if expected_response and 'data' in expected_response:
            custom_ignore = expected_response['data'].get('ignore_fields', [])
            if custom_ignore:
                ignore_fields.extend(custom_ignore)
        
        # Always include ignore_fields in the ignore list (self-reference)
        if 'ignore_fields' not in ignore_fields:
            ignore_fields.append('ignore_fields')
            
        return ignore_fields