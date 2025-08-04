#!/usr/bin/env python3
"""
Data Validation Helper for Test Framework

Validates sorting and filtering results against model metadata.
Works with any Pydantic model that has _metadata attribute.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class DataValidationHelper:
    """Helper class to validate API response data against model metadata"""
    
    def __init__(self, model_class):
        """Initialize with a model class (e.g., User)"""
        self.model_class = model_class
        self.metadata = model_class.get_metadata()
        self.fields = self.metadata.get('fields', {})
    
    def get_enum_values(self, field_name: str) -> Optional[List[str]]:
        """Get valid enum values for a field"""
        field_info = self.fields.get(field_name, {})
        enum_info = field_info.get('enum', {})
        return enum_info.get('values', []) if enum_info else None
    
    def get_field_type(self, field_name: str) -> Optional[str]:
        """Get the type of a field"""
        field_info = self.fields.get(field_name, {})
        return field_info.get('type')
    
    def validate_sort_order(self, data: List[Dict], sort_fields: List[tuple]) -> tuple[bool, str]:
        """
        Validate that returned data is sorted correctly.
        
        Args:
            data: List of records from API response
            sort_fields: List of (field_name, order) tuples e.g. [('firstName', 'asc'), ('lastName', 'desc')]
            
        Returns:
            (is_valid, error_message)
        """
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
                
                # Compare non-None values
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
    
    def validate_filter_results(self, data: List[Dict], filter_criteria: Dict[str, str]) -> tuple[bool, str]:
        """
        Validate that all returned records match the filter criteria.
        
        Args:
            data: List of records from API response  
            filter_criteria: Dict of field:value filters e.g. {'gender': 'male', 'isAccountOwner': 'true'}
            
        Returns:
            (is_valid, error_message)
        """
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
    
    def validate_combined_sort_filter(self, data: List[Dict], sort_fields: List[tuple], 
                                    filter_criteria: Dict[str, str]) -> tuple[bool, str]:
        """
        Validate both sorting and filtering on the same dataset.
        
        Returns:
            (is_valid, error_message)
        """
        # First validate filtering
        filter_valid, filter_msg = self.validate_filter_results(data, filter_criteria)
        if not filter_valid:
            return False, f"Combined validation failed - {filter_msg}"
        
        # Then validate sorting
        sort_valid, sort_msg = self.validate_sort_order(data, sort_fields)
        if not sort_valid:
            return False, f"Combined validation failed - {sort_msg}"
        
        return True, f"Combined validation passed: {filter_msg}, {sort_msg}"
    
    def _compare_values(self, val1: Any, val2: Any, field_name: str) -> int:
        """
        Compare two values based on field type.
        Returns: -1 if val1 < val2, 0 if equal, 1 if val1 > val2
        """
        field_type = self.get_field_type(field_name)
        
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
            # Assume datetime objects or ISO strings
            date1 = val1 if isinstance(val1, datetime) else datetime.fromisoformat(val1.replace('Z', '+00:00'))
            date2 = val2 if isinstance(val2, datetime) else datetime.fromisoformat(val2.replace('Z', '+00:00'))
            if date1 < date2:
                return -1
            elif date1 > date2:
                return 1
            else:
                return 0
        
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
        
        # Default to case-insensitive string comparison to match database behavior
        else:
            str1 = str(val1).lower() if val1 is not None else ''
            str2 = str(val2).lower() if val2 is not None else ''
            
            # Use case-insensitive comparison to match database collation behavior
            if str1 < str2:
                return -1
            elif str1 > str2:
                return 1
            else:
                return 0
    
    def _convert_filter_value(self, field_name: str, filter_value: str) -> Any:
        """
        Convert string filter value to proper type for comparison.
        """
        field_type = self.get_field_type(field_name)
        
        if field_type == 'Boolean':
            return filter_value.lower() in ['true', '1', 'yes']
        elif field_type in ['Integer']:
            return int(filter_value)
        elif field_type in ['Currency', 'Float']:
            return float(filter_value)
        elif field_type == 'String':
            # Check if it's an enum field
            enum_values = self.get_enum_values(field_name)
            if enum_values and filter_value not in enum_values:
                raise ValueError(f"'{filter_value}' is not a valid enum value for {field_name}. Valid values: {enum_values}")
            return filter_value
        else:
            return filter_value  # Keep as string for other types