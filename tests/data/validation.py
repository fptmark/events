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
from app.metadata import MetadataManager, register_entity_metadata, get_entity_metadata


class Validator:
    """
    Clean validation system - validates actual API responses against TestCase expectations.
    """
    
    def __init__(self, test_case, result: Dict, config: Dict, verbose: bool = False):
        self.test_case = test_case
        self.result = result
        self.config = config
        self.verbose = verbose
        self.fk_validation = config.get('fk_validation', '')
        self.view_objects = test_case.view_objects
        
        # Use cached entity metadata (already initialized in base_data.py)
        self.entity_metadata = get_entity_metadata(test_case.entity)
        
        # Determine request type and validation settings
        self.is_single_request = bool(test_case.id)
        self.fk_validation_enabled = self.config.get('fk_validation', '') in ['single', 'multiple']
        
    def validate_test_case(self, http_status) -> bool:
        """Main validation entry point"""
        # Basic structure validation (required for all responses)
        if not self._validate_basic_structure(http_status):
            return False
            
        if http_status not in [200, 201]:
            return True

        # Single entity validation (comprehensive)
        if self.is_single_request:
            return self._validate_single_entity()
            
        # List validation (pagination, sorting, filtering)
        return self._validate_list_response()
    
    # ==================== BASIC STRUCTURE VALIDATION ====================
    
    def _validate_basic_structure(self, http_status) -> bool:
        """Validate basic response structure - applies to all responses"""
        # Must have data field
        if http_status in [200, 201]:
            if 'data' not in self.result:
                print(f"    ❌ Missing 'data' field in response")
                return False
            
            data = self.result['data']
            
            # Single request = single object or null (for not found), List request = array
            if self.is_single_request:
                if isinstance(data, list):
                    print(f"    ❌ Single entity request returned array, expected object or null")
                    return False
                # data can be None/null for non-existent entities (404 responses)
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
        """Validate notification count matches expectation for new notification structure"""
        expected_notifications = self.test_case.expected_response.get('notifications', {})
        actual_notifications = self.result.get('notifications', {})
        
        # Check errors array if expected
        if 'errors' in expected_notifications:
            expected_errors = expected_notifications['errors']
            actual_errors = actual_notifications.get('errors', [])
            if len(expected_errors) != len(actual_errors):
                print(f"    ❌ Errors count mismatch: expected {len(expected_errors)}, got {len(actual_errors)}")
                return False
        
        # Check warnings structure if expected
        if 'warnings' in expected_notifications:
            expected_warnings = self._adjust_fk_validations(expected_notifications.get('warnings', {}))
            actual_warnings = self._adjust_fk_validations(actual_notifications.get('warnings', {}))
            
            # Check each entity/id group
            for entity_type, entity_id_warnings in expected_warnings.items():
                if entity_type not in actual_warnings:
                    # for entity_id in entity_ids:
                    print(f"    ❌ Missing warnings for entity type '{entity_type}'")
                    return False
                    
                for entity_id, expected_warning_list in entity_id_warnings.items():
                    actual_warning_list = actual_warnings[entity_type].get(entity_id, [])
                    if len(expected_warning_list) != len(actual_warning_list):
                        print(f"    ❌ Warning count mismatch for {entity_type}:{entity_id}: expected {len(expected_warning_list)}, got {len(actual_warning_list)}")
                        return False

        return True 
    
    def _adjust_fk_validations(self, warning_obj) -> Dict[str, Any]:
        # warnings needs to ignore fk_validations for now
        adjusted_warnings: Dict[str, Any] = {}
        for entity, all_id_warnings in warning_obj.items():
            adjusted_warnings[entity] = {}
            for id, warning_list in all_id_warnings.items():
                entity_id_warnings = []
                for warning in warning_list:
                    field = warning.get('field', '')
                    message = warning.get('message', '').lower()

                    if not (field.endswith("Id") and ("field required" in message or "does not exist" in message)):
                        entity_id_warnings.append(warning)
                adjusted_warnings[entity][id] = entity_id_warnings
        return adjusted_warnings
            
    def _validate_single_entity(self) -> bool:
        """Comprehensive validation for single entity responses"""
        
        data = self.result.get('data')
        
        # For 404 responses, data should be null
        if self.test_case.expected_status == 404:
            if data is not None:
                print(f"    ❌ 404 response should have data: null, but got: {type(data)}")
                return False
            return True  # 404 with null data is valid
        
        # For 200 responses, data should not be null
        if self.test_case.expected_status == 200:
            if data is None:
                print(f"    ❌ 200 response should have data object, but got: null")
                return False
        
        # Expected response validation (deep field comparison)
        if self.test_case.expected_response:
            if not self._validate_expected_response(self.result):
                return False
        
        # FK sub-object validation (only if data exists)
        if self.fk_validation_enabled or self.test_case.expected_sub_objects:
            if not self._validate_fk_sub_objects(data):
                return False
                
        return True
    
    def _validate_expected_response(self, actual_response: Dict) -> bool:
        """Validate actual data matches expected_response exactly"""
        expected_data = self.test_case.expected_response.get('data', {})
        actual_data = actual_response.get('data', {})
        fields = self.entity_metadata.fields

        # Check that auto fields exist in the actual data
        if self.entity_metadata:
            for field_name, field_info in fields.items():
                if field_info.auto_generate or field_info.auto_update:
                    if field_name not in actual_data or not actual_data[field_name]:
                        if self.verbose:
                            print(f"    ❌ Missing auto-generated field or contents '{field_name}' in actual data")
                        return False
        
        # Compare data fields
        if not self._compare_objects(actual_data, expected_data, "data", fields):
            return False
            
        # Compare warnings if specified (new notification structure)
        expected_warnings = self.test_case.expected_response.get('notifications', {}).get('warnings', {})
        actual_warnings = actual_response.get('notifications', {}).get('warnings', {})
        return self._compare_warnings(actual_warnings, expected_warnings)
        # if expected_notifications.get('warnings'):
        #     entity_type = self.test_case.entity
        #     entity_id = self.test_case.id
            
        #     # Get expected warnings for this entity/id
        #     expected_warnings = expected_notifications.get('warnings', {}).get(entity_type, {}).get(entity_id, [])
        #     if expected_warnings:
        #         actual_warnings = actual_notifications.get('warnings', {}).get(entity_type, {}).get(entity_id, [])
        #         if not self._compare_warnings(actual_warnings, expected_warnings):
        #             return False
                
        # return True
    
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
            
        # Sort validation - parse from URL
        sort_criteria = self.test_case.get_sort_criteria()
        if sort_criteria:
            if not self._validate_sort_order(data, sort_criteria):
                return False
                
        # Filter validation - parse from URL
        filter_criteria = self.test_case.get_filter_criteria()
        if filter_criteria:
            if not self._validate_filtering(data, filter_criteria):
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
    
    def _validate_sort_order(self, data: List[Dict], sort_criteria: List[Tuple[str, str]]) -> bool:
        """Validate data is sorted according to sort criteria with enhanced multiple criteria support"""
        if not sort_criteria:
            return True  # No sort criteria to validate
            
        if len(data) < 2:
            return True  # Can't validate sort with < 2 items
        
        # Get invalid sort fields from APPLICATION errors to skip validation
        invalid_sort_fields = self._get_invalid_sort_fields()
        
        # Filter out invalid sort fields from validation
        valid_sort_criteria = []
        for field_name, direction in sort_criteria:
            if field_name.lower() not in invalid_sort_fields:
                valid_sort_criteria.append((field_name, direction))
        
        # If no valid sort criteria remain, sorting validation passes
        if not valid_sort_criteria:
            return True
        
        # Enhanced validation with better error reporting
        for i in range(len(data) - 1):
            current = data[i]
            next_item = data[i + 1]
            
            if not self._validate_sort_pair(current, next_item, valid_sort_criteria, i):
                return False
                    
        return True
    
    def _validate_sort_pair(self, current: Dict, next_item: Dict, sort_criteria: List[Tuple[str, str]], pair_index: int) -> bool:
        """Validate sort order between two adjacent records"""
        # Check sort order for each field in sequence
        for field_idx, (field_name, direction) in enumerate(sort_criteria):
            current_val = current.get(field_name)
            next_val = next_item.get(field_name)
            
            # Compare values using metadata-aware comparison
            comparison = self._compare_values(current_val, next_val, field_name)
            
            if comparison == 0:
                continue  # Equal values, check next sort field for tie-breaking
                
            # Check if order is correct
            expected_order = comparison <= 0 if direction == 'asc' else comparison >= 0
            
            if not expected_order:
                if self.verbose:
                    direction_text = "ascending" if direction == 'asc' else "descending"
                    sort_context = f"sort field {field_idx + 1}/{len(sort_criteria)} ({field_name} {direction_text})"
                    print(f"    ❌ Sort violation at records {pair_index}-{pair_index + 1}: '{current_val}' vs '{next_val}' for {sort_context}")
                return False
            else:
                # Correct order found, no need to check remaining fields
                break
        
        return True
    
    def _validate_filtering(self, data: List[Dict], filter_criteria: Dict[str, Any]) -> bool:
        """Validate all data items match filter criteria with enhanced multiple criteria support"""
        if not filter_criteria:
            return True
            
        # Get invalid filter fields from APPLICATION errors to skip validation
        invalid_filter_fields = self._get_invalid_filter_fields()
            
        # Group filters by field for better processing of range filters
        field_filters = {}
        for filter_key, expected_value in filter_criteria.items():
            if ':' in filter_key:
                field_name, operator = filter_key.split(':', 1)
                # Skip invalid fields - they're already reported as APPLICATION errors
                if field_name.lower() in invalid_filter_fields:
                    continue
                if field_name not in field_filters:
                    field_filters[field_name] = []
                field_filters[field_name].append((operator, expected_value))
            else:
                field_name = filter_key
                # Skip invalid fields - they're already reported as APPLICATION errors
                if field_name.lower() in invalid_filter_fields:
                    continue
                if field_name not in field_filters:
                    field_filters[field_name] = []
                field_filters[field_name].append(('eq', expected_value))
        
        # Validate each record against all filters (excluding invalid fields)
        for i, record in enumerate(data):
            if not self._validate_record_filters(record, field_filters, i):
                return False
                        
        return True
    
    def _validate_record_filters(self, record: Dict, field_filters: Dict[str, List[Tuple[str, str]]], record_index: int) -> bool:
        """Validate a single record against all field filters"""
        for field_name, filters in field_filters.items():
            # Map field name from filter to actual response field name (case-insensitive)
            actual_field_name = self._map_response_field_name(field_name, record)
            actual_value = record.get(actual_field_name)
            
            # All filters for this field must pass
            for operator, expected_value in filters:
                if operator == 'eq':
                    # Handle string vs non-string field filtering differently
                    field_info = self.entity_metadata.get_field_info(field_name)
                    field_type = field_info.type if field_info else 'String'
                    
                    if field_type == 'String' and not self.entity_metadata.is_enum_field(field_name):
                        # String fields use partial matching (contains) - current server behavior
                        if actual_value is None:
                            if self.verbose:
                                print(f"    ❌ Filter mismatch: Record {record_index} has {actual_field_name}=null, can't contain '{expected_value}'")
                            return False
                        
                        # Case-insensitive partial matching to match server behavior  
                        actual_str = str(actual_value).lower()
                        expected_str = str(expected_value).lower()
                        
                        if expected_str not in actual_str:
                            if self.verbose:
                                print(f"    ❌ Filter mismatch: Record {record_index} has {actual_field_name}='{actual_value}', doesn't contain '{expected_value}'")
                            return False
                    else:
                        # Non-string fields (enums, numbers, dates, etc.) use exact matching
                        expected_typed = self._convert_filter_value(actual_field_name, expected_value)
                        if actual_value != expected_typed:
                            if self.verbose:
                                print(f"    ❌ Filter mismatch: Record {record_index} has {actual_field_name}='{actual_value}', expected '{expected_typed}'")
                            return False
                else:
                    # Comparison filter
                    if not self._validate_comparison_filter(record, actual_field_name, operator, expected_value, record_index):
                        return False
                        
        return True
    
    def _validate_comparison_filter(self, record: Dict, field_name: str, operator: str, expected_value: str, record_index: int) -> bool:
        """Validate comparison filter (gte, lte, gt, lt) for a single record with enhanced type handling"""
        actual_value = record.get(field_name)
        
        # Handle null values - most comparison operators fail on null
        if actual_value is None:
            # Only equality can match null
            if operator == 'eq' and expected_value.lower() in ['null', 'none', '']:
                return True
            else:
                if self.verbose:
                    print(f"    ❌ Filter mismatch: Record {record_index} has {field_name}=null, can't apply {operator} '{expected_value}'")
                return False
        
        # Type-aware conversion with enhanced error handling
        try:
            actual_typed, expected_typed = self._convert_values_for_comparison(actual_value, expected_value, field_name)
        except (ValueError, TypeError) as e:
            if self.verbose:
                print(f"    ❌ Filter error: Record {record_index} - can't compare {field_name}='{actual_value}' {operator} '{expected_value}': {e}")
            return False
        
        # Perform comparison based on operator with better error handling
        try:
            if operator == 'gte':
                result = actual_typed >= expected_typed
            elif operator == 'lte':
                result = actual_typed <= expected_typed
            elif operator == 'gt':
                result = actual_typed > expected_typed
            elif operator == 'lt':
                result = actual_typed < expected_typed
            elif operator == 'eq':
                result = actual_typed == expected_typed
            elif operator == 'ne':
                result = actual_typed != expected_typed
            else:
                if self.verbose:
                    print(f"    ❌ Filter error: Unknown operator '{operator}' for {field_name}")
                return False
        except TypeError as e:
            if self.verbose:
                print(f"    ❌ Filter error: Record {record_index} - incompatible types for {field_name} {operator} comparison: {e}")
            return False
            
        if not result:
            if self.verbose:
                print(f"    ❌ Filter mismatch: Record {record_index} has {field_name}='{actual_value}', failed {operator} '{expected_value}'")
            return False
            
        return True
    
    def _convert_values_for_comparison(self, actual_value: Any, expected_value: str, field_name: str) -> Tuple[Any, Any]:
        """Convert actual and expected values to compatible types for comparison"""
        field_info = self.entity_metadata.get_field_info(field_name)
        field_type = field_info.type if field_info else 'String'
        
        if field_type in ['Integer', 'Currency', 'Float']:
            actual_typed = float(actual_value)
            expected_typed = float(expected_value)
        elif field_type in ['Date', 'Datetime']:
            from datetime import datetime
            
            # Handle actual value
            if isinstance(actual_value, str):
                actual_typed = datetime.fromisoformat(actual_value.replace('Z', '+00:00'))
            elif hasattr(actual_value, 'year'):  # datetime-like object
                actual_typed = actual_value
            else:
                raise ValueError(f"Cannot convert actual value '{actual_value}' to datetime")
            
            # Handle expected value
            if isinstance(expected_value, str):
                # Try different date formats
                try:
                    expected_typed = datetime.fromisoformat(expected_value.replace('Z', '+00:00'))
                except ValueError:
                    # Try date-only format
                    expected_typed = datetime.fromisoformat(f"{expected_value}T00:00:00+00:00")
            else:
                expected_typed = expected_value
                
        elif field_type == 'Boolean':
            actual_typed = bool(actual_value)
            expected_typed = expected_value.lower() in ['true', '1', 'yes', 'on']
        else:
            # String comparison - case insensitive to match server behavior
            actual_typed = str(actual_value).lower()
            expected_typed = str(expected_value).lower()
        
        return actual_typed, expected_typed
    
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
    
    def _compare_objects(self, actual: Dict, expected: Dict, path: str, fields: Optional[Dict[str, Any]] = None) -> bool:
        """Compare two objects field by field"""
        # Check all expected fields are present
        if not fields:
            fields = list(actual.keys())
        for field_name, field_attr in fields.items():
            if field_name not in actual and field_name in expected:
                if self.verbose:
                    print(f"    ❌ Missing expected field '{field_name}' in {path}")
                return False
                
            if field_name not in expected and field_name in actual:
                if self.verbose:
                    print(f"    ❌ Extra actual field '{field_name}' in {path}")
                return False
                
            actual_value = actual.get('field_name', '')
            expected_value = expected.get('field_name', '')
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
    

    def _compare_warnings(self, actual_warnings: Dict[str, Any], expected_warnings: Dict[str, Any]) -> bool:
        # 1) Entities must match
        a_entities = set(actual_warnings.keys())
        e_entities = set(expected_warnings.keys())
        if a_entities != e_entities:
            if self.verbose:
                print(f"❌ Entities differ. missing={e_entities - a_entities}, extra={a_entities - e_entities}")
            return False

        # 2) IDs must match per entity, and 3) counts must match per ID
        for entity, a_ids_map in actual_warnings.items():
            e_ids_map = expected_warnings.get(entity, {})

            a_ids = set(a_ids_map.keys())
            e_ids = set(e_ids_map.keys())
            if a_ids != e_ids:
                if self.verbose:
                    print(f"❌ [{entity}] IDs differ. missing={e_ids - a_ids}, extra={a_ids - e_ids}")
                return False

            for rid in a_ids:
                a_list = a_ids_map.get(rid, []) or []
                e_list = e_ids_map.get(rid, []) or []
                if len(a_list) != len(e_list):
                    if self.verbose:
                        print(f"❌ [{entity}:{rid}] Count mismatch: expected {len(e_list)}, got {len(a_list)}")
                    return False

        return True


    # def _compare_warnings(self, actual_warnings: Dict[str, Any], expected_warnings: Dict[str, Any]) -> bool:
    #     # for each entity type
    #     for actual_entity, actual_id_warnings in actual_warnings:
    #         expected_entity_data = expected_warnings.get(actual_entity) 
    #         for actual_id, actual_warnings in actual_id_warnings.items():
    #     if len(actual_warnings) != len(expected_warnings):
    #         if self.verbose:
    #             print(f"    ❌ Warning count mismatch: expected {len(expected_warnings)}, got {len(actual_warnings)}")
    #         return False
            
    #     # For warnings, we mainly care about field names and types, not exact messages
    #     actual_fields = {w.get('field') for w in actual_warnings}
    #     expected_fields = {w.get('field') for w in expected_warnings}
        
    #     if actual_fields != expected_fields:
    #         if self.verbose:
    #             print(f"    ❌ Warning fields mismatch: expected {expected_fields}, got {actual_fields}")
    #         return False
            
    #     return True
    
    # def _extract_warnings_for_entity(self, entity_id: str) -> List[Dict]:
    #     """Extract warnings for specific entity from new notification structure"""
    #     notifications = self.result.get('notifications', {})
    #     warnings = notifications.get('warnings', {})
        
    #     # Find warnings for this entity across all entity types
    #     entity_type = self.test_case.entity.lower()
    #     entity_warnings = warnings.get(entity_type, {})
    #     return entity_warnings.get(entity_id, [])
    
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
        field_info = self.entity_metadata.get_field_info(field_name)
        field_type = field_info.type if field_info else 'String'
        
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
                    date1, date2 = val1, val2
                else:
                    # Try parsing ISO format
                    date1 = datetime.fromisoformat(str(val1).replace('Z', '+00:00'))
                    date2 = datetime.fromisoformat(str(val2).replace('Z', '+00:00'))
                
                # For auto-generated timestamp fields, add microsecond tolerance to handle
                # sub-millisecond precision differences that occur in rapid record creation
                is_auto_field = self.entity_metadata.is_auto_generated_field(field_name)
                if is_auto_field:
                    # Consider timestamps within 100ms as equal for auto-generated fields
                    time_diff = abs((date1 - date2).total_seconds())
                    if time_diff <= 0.1:  # 100ms tolerance
                        return 0  # Treat as equal
                
                return -1 if date1 < date2 else (1 if date1 > date2 else 0)
            except:
                pass  # Fall through to string comparison
        elif field_type == 'Boolean':
            bool1, bool2 = bool(val1), bool(val2)
            return -1 if bool1 < bool2 else (1 if bool1 > bool2 else 0)
            
        # String comparison - case insensitive to match server behavior
        str1, str2 = str(val1).lower(), str(val2).lower()
        return -1 if str1 < str2 else (1 if str1 > str2 else 0)
    
    def _map_response_field_name(self, filter_field_name: str, record: Dict) -> str:
        """Map filter field name to actual response field name using metadata system"""
        # Use metadata system to get proper field name
        proper_field_name = self.entity_metadata.get_field_name(filter_field_name)
        if proper_field_name and proper_field_name in record:
            return proper_field_name
        
        # If metadata doesn't have it, try exact match
        if filter_field_name in record:
            return filter_field_name
        
        # If no match found, return original (will result in None value during validation)
        return filter_field_name
    
    def _get_invalid_filter_fields(self) -> set:
        """Extract field names that generated application errors from API response."""
        invalid_fields = set()
        
        # Null safety check
        if not self.result or not isinstance(self.result, dict):
            return invalid_fields
        
        # Look for application errors about filter criteria fields
        notifications = self.result.get('notifications')
        if not notifications or not isinstance(notifications, dict):
            return invalid_fields
            
        errors = notifications.get('errors', [])
        if not isinstance(errors, list):
            return invalid_fields
            
        for error in errors:
            if error.get('type') == 'application':
                message = error.get('message', '')
                # Look for "Filter criteria field 'fieldname' does not exist in entity"
                if 'Filter criteria field' in message and 'does not exist in entity' in message:
                    # Extract field name from error message
                    import re
                    match = re.search(r"Filter criteria field '([^']+)' does not exist", message)
                    if match:
                        field_name = match.group(1)
                        invalid_fields.add(field_name.lower())  # Store lowercase for comparison
        
        return invalid_fields
    
    def _get_invalid_sort_fields(self) -> set:
        """Extract field names that generated application errors from API response."""
        invalid_fields = set()
        
        # Null safety check
        if not self.result or not isinstance(self.result, dict):
            return invalid_fields
        
        # Look for application errors about sort criteria fields
        notifications = self.result.get('notifications')
        if not notifications or not isinstance(notifications, dict):
            return invalid_fields
            
        errors = notifications.get('errors', [])
        if not isinstance(errors, list):
            return invalid_fields
            
        for error in errors:
            if error.get('type') == 'application':
                message = error.get('message', '')
                # Look for "Sort criteria field 'fieldname' does not exist in entity"
                if 'Sort criteria field' in message and 'does not exist in entity' in message:
                    # Extract field name from error message
                    import re
                    match = re.search(r"Sort criteria field '([^']+)' does not exist", message)
                    if match:
                        field_name = match.group(1)
                        invalid_fields.add(field_name.lower())  # Store lowercase for comparison
        
        return invalid_fields
    
    def _convert_filter_value(self, field_name: str, filter_value: str) -> Any:
        """Convert string filter value to proper type using metadata"""
        field_info = self.entity_metadata.get_field_info(field_name)
        if not field_info:
            return filter_value  # Return as-is for unknown fields
        
        field_type = field_info.type
        
        if field_type == 'Boolean':
            return filter_value.lower() in ['true', '1', 'yes']
        elif field_type == 'Integer':
            return int(filter_value)
        elif field_type in ['Currency', 'Float']:
            return float(filter_value)
        else:
            return filter_value  # String or other types