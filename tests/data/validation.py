"""
Clean Validation System - Modular, focused validation with comprehensive error handling.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from tests.suites.test_case import TestCase

# TestCase import removed to avoid circular import

def _convert_to_timestamp(value: Any) -> Optional[float]:
    """Convert date/datetime value to Unix timestamp for reliable comparison."""
    try:
        if isinstance(value, (int, float)):
            return float(value)  # Already a timestamp
        elif hasattr(value, 'timestamp'):  # datetime object
            return value.timestamp()
        elif isinstance(value, str):
            # Try various date formats
            try:
                # ISO format with timezone
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.timestamp()
            except ValueError:
                try:
                    # Date only - treat as start of day UTC
                    dt = datetime.fromisoformat(f"{value}T00:00:00+00:00")
                    return dt.timestamp()
                except ValueError:
                    return None
        else:
            return None
    except Exception:
        return None
from urllib.parse import urlparse, parse_qs
from app.services.metadata import MetadataService
# FilterValidator imported locally to avoid circular import

# Add project root to path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# sys.path.insert(0, str(Path(__file__).parent.parent))

class ValidationReporter:
    _verbose: bool = False
    _header: str = ""
    """Static error reporter initialized once per test run."""
    
    def __init__(self, header: str, verbose: bool):
        """Initialize static settings."""
        ValidationReporter._verbose = verbose
        ValidationReporter._header = header
    
    @staticmethod
    def report_error(context: str, message: str, header: Optional[str] = "") -> None:
        """Report validation error if verbose mode is enabled."""
        if not header:
            header = ValidationReporter._header

        try:
            if ValidationReporter._verbose:
                print(f"{header}❌ {context}: {message}")
        except Exception as e:
            ValidationReporter.report_error(f"ValidationReporter.report_error", f"{e}")
            # Don't crash - continue with test execution
    
    @staticmethod
    def check_required_fields(obj: Dict, required_fields: List[str], context: str) -> bool:
        """Check that all required fields are present."""
        try:
            if not obj or not isinstance(obj, dict):
                ValidationReporter.report_error(context, f"Expected dict object, got {type(obj)}")
                return False
            
            for field in required_fields:
                if field not in obj:
                    ValidationReporter.report_error(context, f"Missing required field '{field}'")
                    return False
            return True
        except Exception as e:
            ValidationReporter.report_error(f"ValidationReporter.check_required_fields", f"{e}")
            return False


class FieldTypeConverter:
    """Centralized type conversion and comparison logic with error handling."""
    
    @staticmethod
    def convert_for_comparison(actual_value: Any, expected_value: str, field_info) -> Tuple[Any, Any]:
        """Convert actual and expected values to compatible types for comparison."""
        actual_typed: Any = actual_value
        expected_typed: Any = expected_value
        try:
            field_type = field_info.get('type') if field_info else 'String'
            
            if field_type in ['Integer', 'Currency', 'Float']:
                try:
                    actual_typed = float(actual_value)
                    expected_typed = float(expected_value)
                except (ValueError, TypeError) as e:
                    ValidationReporter.report_error("Cannot convert numeric values", f"actual={actual_value}, expected={expected_value}")
                    
            elif field_type in ['Date', 'Datetime']:
                # Convert to Unix timestamps for reliable comparison
                actual_typed = _convert_to_timestamp(actual_value)
                expected_typed = _convert_to_timestamp(expected_value)
                
                if actual_typed is None or expected_typed is None:
                    ValidationReporter.report_error("Date conversion error", f"actual='{actual_value}', expected='{expected_value}'")
                        
            elif field_type == 'Boolean':
                try:
                    actual_typed = bool(actual_value)
                    expected_typed = expected_value.lower() in ['true', '1', 'yes', 'on']
                except Exception as e:
                    raise ValueError(f"Boolean conversion error", f"{e}")
            else:
                # String comparison - case insensitive to match server behavior
                actual_typed = str(actual_value).lower()
                expected_typed = str(expected_value).lower()
            
            return actual_typed, expected_typed
            
        except Exception as e:
            ValidationReporter.report_error(f"FieldTypeConverter.convert_for_comparison", f"{e}")
            return "", ""
    
    @staticmethod
    def compare_values(val1: Any, val2: Any, field_info) -> int:
        """Compare two values using metadata-aware type handling. Returns -1, 0, or 1."""
        try:
            field_type = field_info.get('type') if field_info else 'String'
            
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
                # Convert to Unix timestamps for simple numeric comparison
                timestamp1 = _convert_to_timestamp(val1)
                timestamp2 = _convert_to_timestamp(val2)
                
                if timestamp1 is not None and timestamp2 is not None:
                    return -1 if timestamp1 < timestamp2 else (1 if timestamp1 > timestamp2 else 0)
                # Fall through to string comparison if conversion fails
                    
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
            ValidationReporter.report_error(f"FieldTypeConverter.compare_values", f"{e}")
            return False


def validate_structure(result: Dict, test_case, http_status: int) -> bool:
    """Main structure validation entry point."""
    try:
        return (validate_data_structure(result, test_case, http_status) and
                validate_notification_structure(result) and
                validate_status_field(result) and
                validate_pagination_structure(result, test_case))
    except Exception as e:
        ValidationReporter.report_error(f"validate_structure", f"{e}")
        return False

def validate_data_structure(result: Dict, test_case, http_status: int) -> bool:
    """Validate data field structure based on request type."""
    # Validate data segment existence and type
    data = result.get('data', None)
    
    if http_status in [200, 201]:
        if not data or len(data) == 0:
            ValidationReporter.report_error("Data Structure", "200/201 response with empty data")
            return False
    elif http_status == 404:
        if data and len(data) != 0:
            ValidationReporter.report_error("Data Structure", "404 response with non-empty data")
            return False    
    else:
        ValidationReporter.report_error("Http Status", f"Unexpected HTTP status {http_status}")
        return False
    return True

def validate_notification_structure(result: Dict) -> bool:
    """Validate notifications structure if present."""
    try:
        if 'notifications' not in result:
            return True  # notifications are optional
        
        notifications = result['notifications']
        if notifications is None:
            return True  # null notifications are valid
        
        if not isinstance(notifications, dict):
            ValidationReporter.report_error("Notification Structure", f"Expected dict, got {type(notifications)}")
            return False
        
        return True
    except Exception as e:
        ValidationReporter.report_error(f"validate_notification_structure", f"{e}")
        return False

def validate_status_field(result: Dict) -> bool:
    """Validate status field."""
    try:
        if 'status' not in result:
            ValidationReporter.report_error("Status Field", "Missing 'status' field")
            return False
        
        status = result['status']
        valid_statuses = ['success', 'warning', 'error']
        if status not in valid_statuses:
            ValidationReporter.report_error("Status Field", f"Invalid status '{status}', expected one of {valid_statuses}")
            return False
        
        return True
    except Exception as e:
        ValidationReporter.report_error(f"validate_status_field", f"{e}")
        return False

def validate_pagination_structure(result: Dict, test_case) -> bool:
    """Validate pagination structure for list responses."""
    try:
        # Pagination only required for list responses
        if not test_case.is_get_all():
            return True
        
        # Pagination fields are under 'pagination' key
        if 'pagination' not in result:
            ValidationReporter.report_error("Pagination", "Missing 'pagination' field")
            return False
            
        pagination_data = result['pagination']
        if pagination_data is None:
            ValidationReporter.report_error("Pagination", "Pagination cannot be null for list responses")
            return False
            
        required_fields = ['page', 'pageSize', 'total', 'totalPages']
        if not ValidationReporter.check_required_fields(pagination_data, required_fields, "Pagination"):
            return False
        
        # Validate pagination bounds
        page = pagination_data.get('page')
        page_size = pagination_data.get('pageSize')
        total = pagination_data.get('total')
        total_pages = pagination_data.get('totalPages')
        
        if page < 1:
            ValidationReporter.report_error("Pagination", f"Invalid page number {page}, must be >= 1")
            return False
            
        if page_size < 1:
            ValidationReporter.report_error("Pagination", f"Invalid pageSize {page_size}, must be >= 1")
            return False
            
        if total < 0:
            ValidationReporter.report_error("Pagination", f"Invalid total {total}, must be >= 0")
            return False
            
        if total_pages < 0:
            ValidationReporter.report_error("Pagination", f"Invalid totalPages {total_pages}, must be >= 0")
            return False
            
        if page > total_pages and total_pages > 0:
            ValidationReporter.report_error("Pagination", f"Page {page} exceeds totalPages {total_pages}")
            return False
        
        # Check for default pagination - when no page specified in request, response should show page 1
        request_url = getattr(test_case, 'url', '')
        if 'page=' not in request_url and pagination_data.get('page') != 1:
            ValidationReporter.report_error("Pagination", f"No page specified in request, but response shows page {pagination_data.get('page')}, expected page 1")
            return False
            
        return True
    except Exception as e:
        ValidationReporter.report_error("validate_pagination_structure", f"{e}")
        return False


def validate_sort_order(test_case, data: List[Dict], sort_criteria: List[Tuple[str, str]], invalid_fields: set) -> bool:
        """Validate data is sorted according to sort criteria."""
        try:
            if not sort_criteria or len(data) < 2:
                return True  # Nothing to validate
            
            # Filter out invalid sort fields
            valid_criteria = [(field, direction) for field, direction in sort_criteria 
                            if field.lower() not in invalid_fields]
            
            if not valid_criteria:
                return True  # No valid criteria to check
            
            # Walk through list and validate sort order
            for i in range(len(data) - 1):
                current_record = data[i]
                next_record = data[i + 1]
                
                # Check each sort field in order
                for field_idx, (field_name, direction) in enumerate(valid_criteria):
                    current_val = current_record.get(field_name)
                    next_val = next_record.get(field_name)
                    
                    # Get field info for proper type-aware comparison
                    field_info = MetadataService.get(test_case.entity, field_name)
                    if not field_info:
                        ValidationReporter.report_error("Cannot find entity field", f"{test_case.entity}.{field_name}")
                    comparison = FieldTypeConverter.compare_values(current_val, next_val, field_info)
                    
                    if comparison == 0:
                        continue  # Equal values, check next sort field
                    
                    # For ascending: current should be <= next (comparison <= 0)
                    # For descending: current should be >= next (comparison >= 0)
                    is_valid_order = (comparison <= 0) if direction == 'asc' else (comparison >= 0)
                    
                    if not is_valid_order:
                        direction_text = "ascending" if direction == 'asc' else "descending"
                        sort_context = f"sort field {field_idx + 1}/{len(valid_criteria)} ({field_name} {direction_text})"
                        ValidationReporter.report_error(f"Sort Order at records {i}-{i + 1}", 
                                                      f"'{current_val}' vs '{next_val}' for {sort_context}")
                        return False
                    else:
                        break  # Correct order found, no need to check remaining fields
            
            return True
        except Exception as e:
            ValidationReporter.report_error("validate_sort_order", f"{e}")
            return False
    


# FilterValidator is now imported from validate_filters.py

# Common field utility functions  
# def get_field_info(test_case, field_name) -> Dict[str, Any]:
#     """Get field metadata information for a given field name."""
#     return MetadataService.get(test_case.entity, field_name) or {}

# def get_field_type(field_info: Dict[str, Any]) -> str:
#     """Extract field type from field info, defaulting to String."""
#     return field_info.get('type', 'String')


def filter_validation_warnings(warnings: dict, bad_view:bool) -> dict:
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
            kept = [w for w in warning_list if not ("FK" in w.get("message") and bad_view)]  # ignore FK validations if the view was bad
            if kept:  # only add if something remains
                filtered[entity][entity_id] = kept

        # remove entity if empty after filtering
        if not filtered[entity]:
            filtered.pop(entity)

    return filtered


def validate_entity_types_match(actual_warnings: Dict, expected_warnings: Dict) -> bool:
    """Validate that entity types match between actual and expected warnings."""
    actual_entities = set(actual_warnings.keys())
    expected_entities = set(expected_warnings.keys())
    
    if actual_entities != expected_entities:
        missing = expected_entities - actual_entities
        extra = actual_entities - expected_entities
        ValidationReporter.report_error("Warning Counts", 
                                      f"Entities differ. missing={missing}, extra={extra}")
        return False
    return True


def validate_entity_warning_counts(entity: str, actual_warnings: Dict, expected_warnings: Dict) -> bool:
    """Validate warning counts for a specific entity."""
    actual_ids_map = actual_warnings[entity]
    expected_ids_map = expected_warnings.get(entity, {})
    
    actual_ids = set(actual_ids_map.keys())
    expected_ids = set(expected_ids_map.keys())
    
    # Check IDs match
    if actual_ids != expected_ids:
        missing = expected_ids - actual_ids
        extra = actual_ids - expected_ids
        ValidationReporter.report_error("Warning Counts", 
                                      f"[{entity}] IDs differ. missing={missing}, extra={extra}")
        return False
    
    # Check warning counts per ID
    for entity_id in actual_ids:
        actual_list = actual_ids_map.get(entity_id, [])
        expected_list = expected_ids_map.get(entity_id, [])
        
        if len(actual_list) != len(expected_list):
            ValidationReporter.report_error("Warning Counts", 
                                          f"[{entity}:{entity_id}] Count mismatch: expected {len(expected_list)}, got {len(actual_list)}")
            return False
    
    return True


def compare_warning_counts(actual_warnings: Dict, expected_warnings: Dict) -> bool:
    """Compare warning counts between actual and expected."""
    try:
        # Check entity types match
        if not validate_entity_types_match(actual_warnings, expected_warnings):
            return False
        
        # Check IDs and counts per entity
        for entity in actual_warnings.keys():
            if not validate_entity_warning_counts(entity, actual_warnings, expected_warnings):
                return False
        
        return True
    except Exception as e:
        ValidationReporter.report_error(f"compare_warning_counts", f"{e}")
        return False


def validate_warning_counts(expected_notifications: Dict, actual_notifications: Dict, bad_view: bool) -> bool:
    """Validate warning counts match expectations."""
    if 'warnings' not in expected_notifications:
        return True
        
    expected_warnings = filter_validation_warnings(expected_notifications.get('warnings', {}), bad_view)
    actual_warnings = filter_validation_warnings(actual_notifications.get('warnings', {}), bad_view)
    
    return compare_warning_counts(actual_warnings, expected_warnings)


def validate_notification_counts(result: Dict, test_case, request_error:bool) -> bool:
    """Validate notification counts match expectations."""
    try:
        if not test_case.expected_response:
            return True
        
        expected_notifications = test_case.expected_response.get('notifications', {})
        actual_notifications = result.get('notifications', {})
        
        # Check errors count
        if not validate_error_counts(expected_notifications, actual_notifications):
            return False
        
        # Check warnings structure
        if not validate_warning_counts(expected_notifications, actual_notifications, request_error):
            return False
        
        return True
    except Exception as e:
        ValidationReporter.report_error(f"validate_notification_counts", f"{e}")
        return False


def validate_error_counts(expected_notifications: Dict, actual_notifications: Dict) -> bool:
    """Validate error counts match expectations."""
    if 'errors' not in expected_notifications:
        return True
        
    expected_errors = expected_notifications['errors']
    actual_errors = actual_notifications.get('errors', [])
    
    if len(expected_errors) != len(actual_errors):
        ValidationReporter.report_error("Notification Counts", 
                                      f"Errors count mismatch: expected {len(expected_errors)}, got {len(actual_errors)}")
        return False
    return True


def validate_auto_fields(result: Dict, test_case) -> bool:
    """Validate actual data matches expected_response exactly."""
    try:
        if not test_case.expected_response:
            return True  # No expected response to validate
        
        expected_data = test_case.expected_response.get('data', {})
        actual_data = result.get('data', {})
        
        # Check auto-generated fields exist
        for field_name, field_info in MetadataService.fields(test_case.entity).items():
                if field_info.get('autoGenerate') or field_info.get('autoUpdate'):
                    if field_name not in actual_data or not actual_data[field_name]:
                        ValidationReporter.report_error("Expected Response", 
                                                      f"Missing auto-generated field '{field_name}' in actual data")
                        return False
        
        # Compare data fields (simplified for now - could be expanded)
        return True
    except Exception as e:
        ValidationReporter.report_error(f"validate_auto_fields", f"{e}")
        return False



def validate_content(result: Dict, test_case, config: Dict, request_error:bool) -> bool:
    """Validate single entity responses with expected data and notification counts."""
    try:
        if test_case.is_get_all():
            return True  # Not a single entity request
        
        return (validate_auto_fields(result, test_case) and
                validate_notification_counts(result, test_case, request_error))
    except Exception as e:
        ValidationReporter.report_error(f"validate_content", f"{e}")
        return False


# ContentValidator class removed - all functionality moved to standalone functions


# Main validation function - replaces ValidationEngine and Validator classes
def validate_test_case(test_case: TestCase, result: Dict, config: Dict, http_status: int) -> bool:
    """Main validation entry point - fail fast approach."""
    try:
        
        # Structure validation
        if not validate_structure(result, test_case, http_status):
            return False

        error_match, request_error = validate_request_response(result, test_case)
        if not error_match:
            return False
        
        if http_status not in [200, 201]:
            return True  # Only validate structure for non-success responses
        
        # Content validation
        if not validate_content(result, test_case, config, request_error):
            return False
        
        # List validation - call validators directly instead of ListValidator wrapper
        if test_case.is_get_all():
            data = result.get('data', [])
            if isinstance(data, list):
                # Sort validation
                sort_criteria = test_case.get_sort_criteria()
                if sort_criteria:
                    if not validate_sort_order(test_case, data, sort_criteria, set()):
                        return False
                
                # Filter validation
                filter_criteria = test_case.get_filter_criteria()
                if filter_criteria:
                    from .validate_filters import FilterValidator
                    filter_validator = FilterValidator(test_case)
                    if not filter_validator.validate_filters(data, filter_criteria, set()):
                        return False
        
        return True
    except Exception as e:
        ValidationReporter.report_error(f"validate_test_case", f"{e}")
        return False

def validate_request_response(result: Dict, testCase:TestCase) -> Tuple[bool, bool]:
    """ Return success/failure and if a request error was encountered"""
    actual_request_warnings = result.get('notifications', {}).get('request_warnings', [])
    pattern = r'view=(\w+)\(([^)]+)\)'
    match = re.match(pattern, testCase.params)

    # Look up the fk record
    if match:
        metadata = MetadataService.get(match.group(1))
        if not metadata:
            return actual_request_warnings[0].get('entity_type', '').lower() == match.group(1).lower(), True
        for f in match.group(2).split(','):
            field = f.strip()
            if not metadata['fields'].get(field, None):
                return actual_request_warnings[0].get('field', '').lower() == field.lower(), True

    return True, False