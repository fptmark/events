"""
Filter Validation Module - Specialized filtering validation with utility functions.
"""

from typing import Dict, List, Any, Tuple
from app.services.metadata import MetadataService
from .validation import ValidationReporter, FieldTypeConverter


# def get_field_info(test_case, field_name) -> Dict[str, Any]:
#     """Get field metadata information for a given field name."""
#     return MetadataService.get(test_case.entity, field_name) or {}


# def get_field_type(field_info: Dict[str, Any]) -> str:
#     """Extract field type from field info, defaulting to String."""
#     return field_info.get('type', 'String')


def map_response_field_name(test_case, field_name: str, record: Dict) -> str:
    """Map filter field name to actual response field name using metadata."""
    try:
        # Use metadata system to get proper field name
        proper_field_name = MetadataService.get_proper_name(test_case.entity, field_name)
        if proper_field_name and proper_field_name in record:
            return proper_field_name
        
        # If metadata doesn't have it, try exact match
        if field_name in record:
            return field_name
        
        # Return original (will result in None value during validation)
        return field_name
    except Exception as e:
        ValidationReporter.report_error(f"map_response_field_name", f"{e}")
        return field_name


class FilterValidator:
    """Specialized filtering validation."""
    
    def __init__(self, test_case):
        self.test_case = test_case
    
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
            ValidationReporter.report_error(f"validate_filters", f"{e}")
            return False
    
    def _group_filters_by_field(self, filter_criteria: Dict[str, Any], invalid_fields: set) -> Dict[str, List[Tuple[str, str]]]:
        """Group filter criteria by field name, excluding invalid fields."""
        try:
            field_filters:Dict[str, Any] = {}
            
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
            ValidationReporter.report_error(f"group_filters_by_field", f"{e}")
            return {}
    
    def _validate_record_filters(self, record: Dict, field_filters: Dict[str, List[Tuple[str, str]]], record_index: int) -> bool:
        """Validate a single record against all field filters."""
        try:
            for field_name, filters in field_filters.items():
                # Map field name using metadata
                actual_field_name = map_response_field_name(self.test_case, field_name, record)
                actual_value = record.get(actual_field_name)
                
                # All filters for this field must pass
                for operator, expected_value in filters:
                    if not self._validate_single_filter(actual_value, operator, expected_value, field_name, record_index):
                        return False
            
            return True
        except Exception as e:
            ValidationReporter.report_error(f"validate_record_filters", f"{e}")
            return False
    
    def _validate_single_filter(self, actual_value: Any, operator: str, expected_value: str, field_name: str, record_index: int) -> bool:
        """Validate a single filter condition."""
        try:
            field_info = MetadataService.get(self.test_case.entity, field_name)
            if not field_info:
                ValidationReporter.report_error("Type lookup failure", f"{self.test_case.entity}.{field_name}")
                return False
            
            if operator == 'eq':
                return self._validate_equality_filter(actual_value, expected_value, field_info, field_name, record_index)
            else:
                return self._validate_comparison_filter(actual_value, operator, expected_value, field_info, field_name, record_index)
        except Exception as e:
            ValidationReporter.report_error(f"validate_single_filter", f"{e}")
            return False
    
    def _validate_equality_filter(self, actual_value: Any, expected_value: str, field_info: Dict, field_name: str, record_index: int) -> bool:
        """Validate equality filter with type-aware comparison."""
        try:
            field_type = MetadataService.get(self.test_case.entity, field_name, 'type')
            if not field_type:
                ValidationReporter.report_error("Type lookup failure", f"{self.test_case.entity}.{field_name}")
                return False
            
            if field_type == 'String' and not (field_info and field_info.get('enum')):
                # String fields use partial matching (contains)
                if actual_value is None:
                    ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                                  f"{field_name}=null, can't contain '{expected_value}'")
                    return False
                
                # Case-insensitive partial matching
                actual_str = str(actual_value).lower()
                expected_str = str(expected_value).lower()
                
                if expected_str not in actual_str:
                    ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                                  f"{field_name}='{actual_value}', doesn't contain '{expected_value}'")
                    return False
            else:
                # Non-string fields use exact matching - use FieldTypeConverter instead of duplicated logic
                expected_typed = self._convert_filter_value_using_field_converter(expected_value, field_info)
                if actual_value != expected_typed:
                    ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                                  f"{field_name}='{actual_value}', expected '{expected_typed}'")
                    return False
            
            return True
        except Exception as e:
            ValidationReporter.report_error(f"validate_equality_filter", f"{e}")
            return False
    
    def _validate_comparison_filter(self, actual_value: Any, operator: str, expected_value: str, field_info: Dict, field_name: str, record_index: int) -> bool:
        """Validate comparison filter (gte, lte, gt, lt, ne)."""
        try:
            # Handle null values
            if actual_value is None:
                if operator == 'eq' and expected_value.lower() in ['null', 'none', '']:
                    return True
                else:
                    ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                                  f"{field_name}=null, can't apply {operator} '{expected_value}'")
                    return False
            
            # Convert values for comparison using FieldTypeConverter
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
                                              f"Unknown operator '{operator}' for {field_name}")
                return False
            
            if not result:
                ValidationReporter.report_error(f"Filter mismatch at record {record_index}", 
                                              f"{field_name}='{actual_value}', failed {operator} '{expected_value}'")
                return False
            
            return True
        except Exception as e:
            ValidationReporter.report_error(f"validate_comparison_filter", f"{e}")
            return False
    
    def _convert_filter_value_using_field_converter(self, filter_value: str, field_info: Dict) -> Any:
        """Convert string filter value to proper type using FieldTypeConverter logic."""
        field_type = get_field_type(field_info)
        
        if field_type == 'Boolean':
            return filter_value.lower() in ['true', '1', 'yes']
        elif field_type == 'Integer':
            return int(filter_value)
        elif field_type in ['Currency', 'Float']:
            return float(filter_value)
        else:
            return filter_value