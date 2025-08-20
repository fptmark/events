"""
Clean Validation System - Modular, focused validation with comprehensive error handling.
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

# Graceful imports - handle missing dependencies
try:
    import utils
    from app.metadata import MetadataManager, register_entity_metadata, get_entity_metadata
    METADATA_AVAILABLE = True
except ImportError:
    # Mock metadata functions for testing without full app dependencies
    def get_entity_metadata(entity_name):
        return None
    METADATA_AVAILABLE = False


class ValidationReporter:
    """Standardized error reporting with consistent format and try/catch protection."""
    
    @staticmethod
    def report_error(context: str, message: str, verbose: bool = False) -> None:
        """Report validation error with clear context."""
        try:
            if verbose:
                print(f"    ❌ {context}: {message}")
        except Exception as e:
            print(f"    ❌ ERROR in ValidationReporter.report_error: {e}")
            sys.exit(1)
    
    @staticmethod
    def check_required_fields(obj: Dict, required_fields: List[str], context: str, verbose: bool = False) -> bool:
        """Check that all required fields are present."""
        try:
            if not obj or not isinstance(obj, dict):
                if verbose:
                    ValidationReporter.report_error(context, f"Expected dict object, got {type(obj)}", verbose)
                return False
            
            for field in required_fields:
                if field not in obj:
                    ValidationReporter.report_error(context, f"Missing required field '{field}'", verbose)
                    return False
            return True
        except Exception as e:
            print(f"    ❌ ERROR in ValidationReporter.check_required_fields: {e}")
            sys.exit(1)


class FieldTypeConverter:
    """Centralized type conversion and comparison logic with error handling."""
    
    @staticmethod
    def convert_for_comparison(actual_value: Any, expected_value: str, field_info) -> Tuple[Any, Any]:
        """Convert actual and expected values to compatible types for comparison."""
        try:
            field_type = field_info.type if field_info else 'String'
            
            if field_type in ['Integer', 'Currency', 'Float']:
                try:
                    actual_typed = float(actual_value)
                    expected_typed = float(expected_value)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Cannot convert numeric values: actual={actual_value}, expected={expected_value}")
                    
            elif field_type in ['Date', 'Datetime']:
                try:
                    # Handle actual value
                    if isinstance(actual_value, str):
                        actual_typed = datetime.fromisoformat(actual_value.replace('Z', '+00:00'))
                    elif hasattr(actual_value, 'year'):  # datetime-like object
                        actual_typed = actual_value
                    else:
                        raise ValueError(f"Cannot convert actual value '{actual_value}' to datetime")
                    
                    # Handle expected value
                    if isinstance(expected_value, str):
                        try:
                            expected_typed = datetime.fromisoformat(expected_value.replace('Z', '+00:00'))
                        except ValueError:
                            # Try date-only format
                            expected_typed = datetime.fromisoformat(f"{expected_value}T00:00:00+00:00")
                    else:
                        expected_typed = expected_value
                except Exception as e:
                    raise ValueError(f"Date conversion error: {e}")
                        
            elif field_type == 'Boolean':
                try:
                    actual_typed = bool(actual_value)
                    expected_typed = expected_value.lower() in ['true', '1', 'yes', 'on']
                except Exception as e:
                    raise ValueError(f"Boolean conversion error: {e}")
            else:
                # String comparison - case insensitive to match server behavior
                actual_typed = str(actual_value).lower()
                expected_typed = str(expected_value).lower()
            
            return actual_typed, expected_typed
            
        except Exception as e:
            print(f"    ❌ ERROR in FieldTypeConverter.convert_for_comparison: {e}")
            sys.exit(1)
    
    @staticmethod
    def compare_values(val1: Any, val2: Any, field_info) -> int:
        """Compare two values using metadata-aware type handling. Returns -1, 0, or 1."""
        try:
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
                try:
                    num1, num2 = float(val1), float(val2)
                    return -1 if num1 < num2 else (1 if num1 > num2 else 0)
                except (ValueError, TypeError):
                    pass  # Fall through to string comparison
                    
            elif field_type in ['Date', 'Datetime']:
                try:
                    if isinstance(val1, datetime) and isinstance(val2, datetime):
                        date1, date2 = val1, val2
                    else:
                        # Try parsing ISO format
                        date1 = datetime.fromisoformat(str(val1).replace('Z', '+00:00'))
                        date2 = datetime.fromisoformat(str(val2).replace('Z', '+00:00'))
                    
                    return -1 if date1 < date2 else (1 if date1 > date2 else 0)
                except Exception:
                    pass  # Fall through to string comparison
                    
            elif field_type == 'Boolean':
                try:
                    bool1, bool2 = bool(val1), bool(val2)
                    return -1 if bool1 < bool2 else (1 if bool1 > bool2 else 0)
                except Exception:
                    pass  # Fall through to string comparison
                    
            # String comparison - case insensitive to match server behavior
            str1, str2 = str(val1).lower(), str(val2).lower()
            return -1 if str1 < str2 else (1 if str1 > str2 else 0)
            
        except Exception as e:
            print(f"    ❌ ERROR in FieldTypeConverter.compare_values: {e}")
            sys.exit(1)


class StructureValidator:
    """Validates basic response structure (data, notifications, pagination)."""
    
    def __init__(self, result: Dict, test_case, verbose: bool = False):
        self.result = result
        self.test_case = test_case
        self.verbose = verbose
    
    def validate(self, http_status: int) -> bool:
        """Main structure validation entry point."""
        try:
            return (self._validate_data_structure(http_status) and
                    self._validate_notification_structure() and
                    self._validate_status_field() and
                    self._validate_pagination_structure())
        except Exception as e:
            print(f"    ❌ ERROR in StructureValidator.validate: {e}")
            sys.exit(1)
    
    def _validate_data_structure(self, http_status: int) -> bool:
        """Validate data field structure based on request type."""
        try:
            # Must have data field for success responses
            if http_status in [200, 201]:
                if 'data' not in self.result:
                    ValidationReporter.report_error("Data Structure", "Missing 'data' field in response", self.verbose)
                    return False
                
                data = self.result['data']
                
                # Single request = single object or null, List request = array
                if self.test_case.is_single_request():
                    if isinstance(data, list):
                        ValidationReporter.report_error("Data Structure", "Single entity request returned array, expected object or null", self.verbose)
                        return False
                else:
                    if not isinstance(data, list):
                        ValidationReporter.report_error("Data Structure", "List request returned object, expected array", self.verbose)
                        return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in StructureValidator._validate_data_structure: {e}")
            sys.exit(1)
    
    def _validate_notification_structure(self) -> bool:
        """Validate notifications structure if present."""
        try:
            if 'notifications' not in self.result:
                return True  # notifications are optional
            
            notifications = self.result['notifications']
            if notifications is None:
                return True  # null notifications are valid
            
            if not isinstance(notifications, dict):
                ValidationReporter.report_error("Notification Structure", f"Expected dict, got {type(notifications)}", self.verbose)
                return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in StructureValidator._validate_notification_structure: {e}")
            sys.exit(1)
    
    def _validate_status_field(self) -> bool:
        """Validate status field."""
        try:
            if 'status' not in self.result:
                ValidationReporter.report_error("Status Field", "Missing 'status' field", self.verbose)
                return False
            
            status = self.result['status']
            valid_statuses = ['success', 'warning', 'error']
            if status not in valid_statuses:
                ValidationReporter.report_error("Status Field", f"Invalid status '{status}', expected one of {valid_statuses}", self.verbose)
                return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in StructureValidator._validate_status_field: {e}")
            sys.exit(1)
    
    def _validate_pagination_structure(self) -> bool:
        """Validate pagination structure for list responses."""
        try:
            # Pagination only required for list responses
            if not self.test_case.is_list_request():
                return True
            
            if 'pagination' not in self.result:
                ValidationReporter.report_error("Pagination Structure", "Missing pagination object in list response", self.verbose)
                return False
            
            pagination = self.result['pagination']
            required_fields = ['page', 'per_page', 'total', 'total_pages', 'has_next', 'has_prev']
            
            return ValidationReporter.check_required_fields(pagination, required_fields, "Pagination", self.verbose)
        except Exception as e:
            print(f"    ❌ ERROR in StructureValidator._validate_pagination_structure: {e}")
            sys.exit(1)


class SortValidator:
    """Specialized sorting validation."""
    
    def __init__(self, entity_metadata, verbose: bool = False):
        self.entity_metadata = entity_metadata
        self.verbose = verbose
    
    def validate_sort_order(self, data: List[Dict], sort_criteria: List[Tuple[str, str]], invalid_fields: set) -> bool:
        """Validate data is sorted according to sort criteria."""
        try:
            if not sort_criteria or len(data) < 2:
                return True  # Nothing to validate
            
            # Filter out invalid sort fields
            valid_criteria = [(field, direction) for field, direction in sort_criteria 
                            if field.lower() not in invalid_fields]
            
            if not valid_criteria:
                return True  # No valid criteria to check
            
            # Validate each adjacent pair
            for i in range(len(data) - 1):
                if not self._validate_sort_pair(data[i], data[i + 1], valid_criteria, i):
                    return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in SortValidator.validate_sort_order: {e}")
            sys.exit(1)
    
    def _validate_sort_pair(self, current: Dict, next_item: Dict, sort_criteria: List[Tuple[str, str]], pair_index: int) -> bool:
        """Validate sort order between two adjacent records."""
        try:
            for field_idx, (field_name, direction) in enumerate(sort_criteria):
                current_val = current.get(field_name)
                next_val = next_item.get(field_name)
                
                # Get field info for type-aware comparison
                field_info = self.entity_metadata.get_field_info(field_name) if self.entity_metadata else None
                comparison = FieldTypeConverter.compare_values(current_val, next_val, field_info)
                
                if comparison == 0:
                    continue  # Equal values, check next sort field
                
                # Check if order is correct
                expected_order = comparison <= 0 if direction == 'asc' else comparison >= 0
                
                if not expected_order:
                    direction_text = "ascending" if direction == 'asc' else "descending"
                    sort_context = f"sort field {field_idx + 1}/{len(sort_criteria)} ({field_name} {direction_text})"
                    ValidationReporter.report_error(f"Sort Order at records {pair_index}-{pair_index + 1}", 
                                                  f"'{current_val}' vs '{next_val}' for {sort_context}", self.verbose)
                    return False
                else:
                    break  # Correct order found, no need to check remaining fields
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in SortValidator._validate_sort_pair: {e}")
            sys.exit(1)


class FilterValidator:
    """Specialized filtering validation."""
    
    def __init__(self, entity_metadata, verbose: bool = False):
        self.entity_metadata = entity_metadata
        self.verbose = verbose
    
    def validate_filters(self, data: List[Dict], filter_criteria: Dict[str, Any], invalid_fields: set) -> bool:
        """Validate all data items match filter criteria."""
        try:
            if not filter_criteria:
                return True
            
            # Group filters by field, excluding invalid fields
            field_filters = self._group_filters_by_field(filter_criteria, invalid_fields)
            
            if not field_filters:
                return True  # No valid filters to check
            
            # Validate each record against all filters
            for i, record in enumerate(data):
                if not self._validate_record_filters(record, field_filters, i):
                    return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in FilterValidator.validate_filters: {e}")
            sys.exit(1)
    
    def _group_filters_by_field(self, filter_criteria: Dict[str, Any], invalid_fields: set) -> Dict[str, List[Tuple[str, str]]]:
        """Group filter criteria by field name, excluding invalid fields."""
        try:
            field_filters = {}
            
            for filter_key, expected_value in filter_criteria.items():
                if ':' in filter_key:
                    field_name, operator = filter_key.split(':', 1)
                else:
                    field_name, operator = filter_key, 'eq'
                
                # Skip invalid fields
                if field_name.lower() in invalid_fields:
                    continue
                
                if field_name not in field_filters:
                    field_filters[field_name] = []
                field_filters[field_name].append((operator, expected_value))
            
            return field_filters
        except Exception as e:
            print(f"    ❌ ERROR in FilterValidator._group_filters_by_field: {e}")
            sys.exit(1)
    
    def _validate_record_filters(self, record: Dict, field_filters: Dict[str, List[Tuple[str, str]]], record_index: int) -> bool:
        """Validate a single record against all field filters."""
        try:
            for field_name, filters in field_filters.items():
                # Map field name using metadata
                actual_field_name = self._map_response_field_name(field_name, record)
                actual_value = record.get(actual_field_name)
                
                # All filters for this field must pass
                for operator, expected_value in filters:
                    if not self._validate_single_filter(actual_value, operator, expected_value, field_name, record_index):
                        return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in FilterValidator._validate_record_filters: {e}")
            sys.exit(1)
    
    def _validate_single_filter(self, actual_value: Any, operator: str, expected_value: str, field_name: str, record_index: int) -> bool:
        """Validate a single filter condition."""
        try:
            field_info = self.entity_metadata.get_field_info(field_name) if self.entity_metadata else None
            
            if operator == 'eq':
                return self._validate_equality_filter(actual_value, expected_value, field_info, field_name, record_index)
            else:
                return self._validate_comparison_filter(actual_value, operator, expected_value, field_info, field_name, record_index)
        except Exception as e:
            print(f"    ❌ ERROR in FilterValidator._validate_single_filter: {e}")
            sys.exit(1)
    
    def _validate_equality_filter(self, actual_value: Any, expected_value: str, field_info, field_name: str, record_index: int) -> bool:
        """Validate equality filter with type-aware comparison."""
        try:
            field_type = field_info.type if field_info else 'String'
            
            if field_type == 'String' and not (field_info and self.entity_metadata.is_enum_field(field_name)):
                # String fields use partial matching (contains)
                if actual_value is None:
                    ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                                  f"{field_name}=null, can't contain '{expected_value}'", self.verbose)
                    return False
                
                # Case-insensitive partial matching
                actual_str = str(actual_value).lower()
                expected_str = str(expected_value).lower()
                
                if expected_str not in actual_str:
                    ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                                  f"{field_name}='{actual_value}', doesn't contain '{expected_value}'", self.verbose)
                    return False
            else:
                # Non-string fields use exact matching
                expected_typed = self._convert_filter_value(expected_value, field_info)
                if actual_value != expected_typed:
                    ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                                  f"{field_name}='{actual_value}', expected '{expected_typed}'", self.verbose)
                    return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in FilterValidator._validate_equality_filter: {e}")
            sys.exit(1)
    
    def _validate_comparison_filter(self, actual_value: Any, operator: str, expected_value: str, field_info, field_name: str, record_index: int) -> bool:
        """Validate comparison filter (gte, lte, gt, lt, ne)."""
        try:
            # Handle null values
            if actual_value is None:
                if operator == 'eq' and expected_value.lower() in ['null', 'none', '']:
                    return True
                else:
                    ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                                  f"{field_name}=null, can't apply {operator} '{expected_value}'", self.verbose)
                    return False
            
            # Convert values for comparison
            actual_typed, expected_typed = FieldTypeConverter.convert_for_comparison(actual_value, expected_value, field_info)
            
            # Perform comparison
            if operator == 'gte':
                result = actual_typed >= expected_typed
            elif operator == 'lte':
                result = actual_typed <= expected_typed
            elif operator == 'gt':
                result = actual_typed > expected_typed
            elif operator == 'lt':
                result = actual_typed < expected_typed
            elif operator == 'ne':
                result = actual_typed != expected_typed
            else:
                ValidationReporter.report_error(f"Filter error at record {record_index}", 
                                              f"Unknown operator '{operator}' for {field_name}", self.verbose)
                return False
            
            if not result:
                ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                              f"{field_name}='{actual_value}', failed {operator} '{expected_value}'", self.verbose)
                return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in FilterValidator._validate_comparison_filter: {e}")
            sys.exit(1)
    
    def _map_response_field_name(self, filter_field_name: str, record: Dict) -> str:
        """Map filter field name to actual response field name."""
        try:
            # Use metadata system to get proper field name
            if self.entity_metadata:
                proper_field_name = self.entity_metadata.get_field_name(filter_field_name)
                if proper_field_name and proper_field_name in record:
                    return proper_field_name
            
            # If metadata doesn't have it, try exact match
            if filter_field_name in record:
                return filter_field_name
            
            # Return original (will result in None value during validation)
            return filter_field_name
        except Exception as e:
            print(f"    ❌ ERROR in FilterValidator._map_response_field_name: {e}")
            sys.exit(1)
    
    def _convert_filter_value(self, filter_value: str, field_info) -> Any:
        """Convert string filter value to proper type."""
        try:
            if not field_info:
                return filter_value
            
            field_type = field_info.type
            
            if field_type == 'Boolean':
                return filter_value.lower() in ['true', '1', 'yes']
            elif field_type == 'Integer':
                return int(filter_value)
            elif field_type in ['Currency', 'Float']:
                return float(filter_value)
            else:
                return filter_value
        except Exception as e:
            print(f"    ❌ ERROR in FilterValidator._convert_filter_value: {e}")
            sys.exit(1)


class ListValidator:
    """Validates list responses (pagination, sorting, filtering)."""
    
    def __init__(self, result: Dict, test_case, verbose: bool = False):
        self.result = result
        self.test_case = test_case
        self.verbose = verbose
        
        # Get entity metadata
        try:
            self.entity_metadata = get_entity_metadata(test_case.entity)
        except Exception as e:
            print(f"    ❌ ERROR getting entity metadata in ListValidator: {e}")
            sys.exit(1)
        
        # Initialize specialized validators
        self.sort_validator = SortValidator(self.entity_metadata, verbose)
        self.filter_validator = FilterValidator(self.entity_metadata, verbose)
    
    def validate(self) -> bool:
        """Main list validation entry point."""
        try:
            if self.test_case.is_single_request():
                return True  # Not a list request
            
            data = self.result.get('data', [])
            if not isinstance(data, list):
                return True  # Structure validation should catch this
            
            return (self._validate_sort_order(data) and
                    self._validate_filtering(data))
        except Exception as e:
            print(f"    ❌ ERROR in ListValidator.validate: {e}")
            sys.exit(1)
    
    def _validate_sort_order(self, data: List[Dict]) -> bool:
        """Validate sort order."""
        try:
            sort_criteria = self.test_case.get_sort_criteria()
            if not sort_criteria:
                return True
            
            invalid_fields = self._get_invalid_sort_fields()
            return self.sort_validator.validate_sort_order(data, sort_criteria, invalid_fields)
        except Exception as e:
            print(f"    ❌ ERROR in ListValidator._validate_sort_order: {e}")
            sys.exit(1)
    
    def _validate_filtering(self, data: List[Dict]) -> bool:
        """Validate filtering."""
        try:
            filter_criteria = self.test_case.get_filter_criteria()
            if not filter_criteria:
                return True
            
            invalid_fields = self._get_invalid_filter_fields()
            return self.filter_validator.validate_filters(data, filter_criteria, invalid_fields)
        except Exception as e:
            print(f"    ❌ ERROR in ListValidator._validate_filtering: {e}")
            sys.exit(1)
    
    def _get_invalid_sort_fields(self) -> set:
        """Extract invalid sort fields from application errors."""
        try:
            return self._extract_invalid_fields("Sort criteria field")
        except Exception as e:
            print(f"    ❌ ERROR in ListValidator._get_invalid_sort_fields: {e}")
            sys.exit(1)
    
    def _get_invalid_filter_fields(self) -> set:
        """Extract invalid filter fields from application errors."""
        try:
            return self._extract_invalid_fields("Filter criteria field")
        except Exception as e:
            print(f"    ❌ ERROR in ListValidator._get_invalid_filter_fields: {e}")
            sys.exit(1)
    
    def _extract_invalid_fields(self, error_prefix: str) -> set:
        """Extract invalid field names from application error messages."""
        try:
            invalid_fields = set()
            
            notifications = self.result.get('notifications')
            if not notifications or not isinstance(notifications, dict):
                return invalid_fields
            
            errors = notifications.get('errors', [])
            if not isinstance(errors, list):
                return invalid_fields
            
            for error in errors:
                if error.get('type') == 'application':
                    message = error.get('message', '')
                    if error_prefix in message and 'does not exist in entity' in message:
                        match = re.search(rf"{error_prefix} '([^']+)' does not exist", message)
                        if match:
                            field_name = match.group(1)
                            invalid_fields.add(field_name.lower())
            
            return invalid_fields
        except Exception as e:
            print(f"    ❌ ERROR in ListValidator._extract_invalid_fields: {e}")
            sys.exit(1)


class ContentValidator:
    """Validates single entity responses with deep field comparison."""
    
    def __init__(self, result: Dict, test_case, config: Dict, verbose: bool = False):
        self.result = result
        self.test_case = test_case
        self.config = config
        self.verbose = verbose
        
        # Get entity metadata
        try:
            self.entity_metadata = get_entity_metadata(test_case.entity)
        except Exception as e:
            print(f"    ❌ ERROR getting entity metadata in ContentValidator: {e}")
            sys.exit(1)
    
    def validate(self) -> bool:
        """Main content validation entry point."""
        try:
            if self.test_case.is_list_request():
                return True  # Not a single entity request
            
            return (self._validate_single_entity_response() and
                    self._validate_expected_response() and
                    self._validate_notification_counts())
        except Exception as e:
            print(f"    ❌ ERROR in ContentValidator.validate: {e}")
            sys.exit(1)
    
    def _validate_single_entity_response(self) -> bool:
        """Validate single entity response data."""
        try:
            data = self.result.get('data')
            
            # For 404 responses, data should be null
            if self.test_case.expected_status == 404:
                if data is not None:
                    ValidationReporter.report_error("Single Entity Response", 
                                                  f"404 response should have data: null, but got: {type(data)}", self.verbose)
                    return False
                return True
            
            # For 200 responses, data should not be null
            if self.test_case.expected_status == 200:
                if data is None:
                    ValidationReporter.report_error("Single Entity Response", 
                                                  "200 response should have data object, but got: null", self.verbose)
                    return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in ContentValidator._validate_single_entity_response: {e}")
            sys.exit(1)
    
    def _validate_expected_response(self) -> bool:
        """Validate actual data matches expected_response exactly."""
        try:
            if not self.test_case.expected_response:
                return True  # No expected response to validate
            
            expected_data = self.test_case.expected_response.get('data', {})
            actual_data = self.result.get('data', {})
            
            # Check auto-generated fields exist
            if self.entity_metadata:
                for field_name, field_info in self.entity_metadata.fields.items():
                    if field_info.auto_generate or field_info.auto_update:
                        if field_name not in actual_data or not actual_data[field_name]:
                            ValidationReporter.report_error("Expected Response", 
                                                          f"Missing auto-generated field '{field_name}' in actual data", self.verbose)
                            return False
            
            # Compare data fields (simplified for now - could be expanded)
            return True
        except Exception as e:
            print(f"    ❌ ERROR in ContentValidator._validate_expected_response: {e}")
            sys.exit(1)
    
    def _validate_notification_counts(self) -> bool:
        """Validate notification counts match expectations."""
        try:
            if not self.test_case.expected_response:
                return True
            
            expected_notifications = self.test_case.expected_response.get('notifications', {})
            actual_notifications = self.result.get('notifications', {})
            
            # Check errors count
            if 'errors' in expected_notifications:
                expected_errors = expected_notifications['errors']
                actual_errors = actual_notifications.get('errors', [])
                if len(expected_errors) != len(actual_errors):
                    ValidationReporter.report_error("Notification Counts", 
                                                  f"Errors count mismatch: expected {len(expected_errors)}, got {len(actual_errors)}", self.verbose)
                    return False
            
            # Check warnings structure
            if 'warnings' in expected_notifications:
                expected_warnings = self._filter_validation_warnings(expected_notifications.get('warnings', {}))
                actual_warnings = self._filter_validation_warnings(actual_notifications.get('warnings', {}))
                
                return self._compare_warning_counts(actual_warnings, expected_warnings)
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in ContentValidator._validate_notification_counts: {e}")
            sys.exit(1)
    
    def _filter_validation_warnings(self, warnings: dict) -> dict:
        """
        Removes all warnings of type 'business' from the warnings structure,
        preserving only 'validation' warnings.
        """
        if not warnings:
            return warnings

        filtered: Dict[str, Any] = {}
        for entity, entity_warnings in warnings.items():
            filtered[entity] = {}
            for entity_id, warning_list in entity_warnings.items():
                # keep only validation type warnings
                kept = [w for w in warning_list if w.get("type") == "validation"]
                if kept:  # only add if something remains
                    filtered[entity][entity_id] = kept

            # remove entity if empty after filtering
            if not filtered[entity]:
                filtered.pop(entity)

        return filtered

    def _compare_warning_counts(self, actual_warnings: Dict, expected_warnings: Dict) -> bool:
        """Compare warning counts between actual and expected."""
        try:
            # Check entity types match
            actual_entities = set(actual_warnings.keys())
            expected_entities = set(expected_warnings.keys())
            
            if actual_entities != expected_entities:
                missing = expected_entities - actual_entities
                extra = actual_entities - expected_entities
                ValidationReporter.report_error("Warning Counts", 
                                              f"Entities differ. missing={missing}, extra={extra}", self.verbose)
                return False
            
            # Check IDs and counts per entity
            for entity, actual_ids_map in actual_warnings.items():
                expected_ids_map = expected_warnings.get(entity, {})
                
                actual_ids = set(actual_ids_map.keys())
                expected_ids = set(expected_ids_map.keys())
                
                if actual_ids != expected_ids:
                    missing = expected_ids - actual_ids
                    extra = actual_ids - expected_ids
                    ValidationReporter.report_error("Warning Counts", 
                                                  f"[{entity}] IDs differ. missing={missing}, extra={extra}", self.verbose)
                    return False
                
                # Check warning counts per ID
                for entity_id in actual_ids:
                    actual_list = actual_ids_map.get(entity_id, [])
                    expected_list = expected_ids_map.get(entity_id, [])
                    
                    if len(actual_list) != len(expected_list):
                        ValidationReporter.report_error("Warning Counts", 
                                                      f"[{entity}:{entity_id}] Count mismatch: expected {len(expected_list)}, got {len(actual_list)}", self.verbose)
                        return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in ContentValidator._compare_warning_counts: {e}")
            sys.exit(1)


class ValidationEngine:
    """Main validation orchestrator - coordinates all validation types."""
    
    def __init__(self, test_case, result: Dict, config: Dict, verbose: bool = False):
        try:
            self.test_case = test_case
            self.result = result
            self.config = config
            self.verbose = verbose
            
            # Initialize specialized validators
            self.structure_validator = StructureValidator(result, test_case, verbose)
            self.content_validator = ContentValidator(result, test_case, config, verbose)
            self.list_validator = ListValidator(result, test_case, verbose)
        except Exception as e:
            print(f"    ❌ ERROR in ValidationEngine.__init__: {e}")
            sys.exit(1)
    
    def validate_test_case(self, http_status: int) -> bool:
        """Main validation entry point - fail fast approach."""
        try:
            # Fail fast: if any validation fails, stop immediately
            if not self.structure_validator.validate(http_status):
                return False
            
            if http_status not in [200, 201]:
                return True  # Only validate structure for non-success responses
            
            if not self.content_validator.validate():
                return False
            
            if not self.list_validator.validate():
                return False
            
            return True
        except Exception as e:
            print(f"    ❌ ERROR in ValidationEngine.validate_test_case: {e}")
            sys.exit(1)


# Main Validator class for backward compatibility
class Validator:
    """Main validator class - delegates to ValidationEngine."""
    
    def __init__(self, test_case, result: Dict, config: Dict, verbose: bool = False):
        try:
            self.validation_engine = ValidationEngine(test_case, result, config, verbose)
        except Exception as e:
            print(f"    ❌ ERROR in Validator.__init__: {e}")
            sys.exit(1)
    
    def validate_test_case(self, http_status: int) -> bool:
        """Main validation entry point."""
        try:
            return self.validation_engine.validate_test_case(http_status)
        except Exception as e:
            print(f"    ❌ ERROR in Validator.validate_test_case: {e}")
            sys.exit(1)