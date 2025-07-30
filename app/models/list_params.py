"""
List parameters for pagination, sorting, and filtering.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union
import re
from app.notification import notify_error


@dataclass
class ListParams:
    """Parameters for paginated, sorted, and filtered entity lists."""
    
    page: int = 1
    page_size: int = 25
    sort_field: Optional[str] = None
    sort_order: str = "asc"  # "asc" or "desc"
    filters: Dict[str, Any] = field(default_factory=dict)   # field=value or field=[min:max]
    
    @property
    def skip(self) -> int:
        """Calculate the number of records to skip for pagination."""
        return (self.page - 1) * self.page_size
    
    @classmethod
    def from_query_params(cls, query_params: Dict[str, str]) -> 'ListParams':
        """Create ListParams from URL query parameters."""
        params = cls()
        
        for key, value in query_params.items():
            try:
                if key == 'page':
                    page_val = int(value)
                    if page_val < 1:
                        notify_error(f"Page number must be >= 1, got: {value}")
                        params.page = 1
                    else:
                        params.page = page_val
                elif key == 'pageSize':
                    size_val = int(value)
                    if size_val < 1:
                        notify_error(f"Page size must be >= 1, got: {value}")
                        params.page_size = 25
                    elif size_val > 1000:
                        notify_error(f"Page size cannot exceed 1000, got: {value}")
                        params.page_size = 1000
                    else:
                        params.page_size = size_val
                elif key == 'sort':
                    params.sort_field = value
                elif key == 'order':
                    if value not in ['asc', 'desc']:
                        notify_error(f"Sort order must be 'asc' or 'desc', got: {value}")
                        params.sort_order = 'asc'
                    else:
                        params.sort_order = value
                elif key == 'view':
                    # Skip view parameter - it's handled separately by the router
                    continue
                elif key == 'filter':
                    # Parse filter parameter: field:value,field2:value2,field3:gt:value3
                    params.filters = cls._parse_filter_parameter(value)
                else:
                    # Unknown parameter - ignore with warning
                    notify_error(f"Unknown query parameter '{key}' ignored. Use 'filter=' for field filtering.")
            except ValueError as e:
                notify_error(f"Invalid parameter '{key}={value}': {str(e)}")
                continue
        
        return params
    
    @staticmethod
    def _parse_filter_parameter(filter_str: str) -> Dict[str, Any]:
        """Parse filter parameter string into filters dict.
        
        Format: field:value,field2:value2,field3:gt:value3,field4:range:[min:max]
        
        Supported operators:
        - field:value (exact match)
        - field:gt:value (greater than)
        - field:gte:value (greater than or equal)
        - field:lt:value (less than)  
        - field:lte:value (less than or equal)
        - field:range:[min:max] (range filter)
        """
        filters = {}
        
        if not filter_str or not filter_str.strip():
            return filters
            
        try:
            # Split by comma for multiple filters
            filter_parts = filter_str.split(',')
            
            for filter_part in filter_parts:
                filter_part = filter_part.strip()
                if not filter_part:
                    continue
                    
                # Split by colon - minimum 2 parts (field:value)
                parts = filter_part.split(':', 2)
                if len(parts) < 2:
                    notify_error(f"Invalid filter format: '{filter_part}'. Use field:value")
                    continue
                    
                field_name = parts[0].strip()
                if not field_name:
                    notify_error(f"Empty field name in filter: '{filter_part}'")
                    continue
                
                if len(parts) == 2:
                    # Simple format: field:value
                    operator = "eq"
                    value = parts[1].strip()
                else:
                    # Extended format: field:operator:value
                    operator = parts[1].strip().lower()
                    value = parts[2].strip()
                
                # Parse the filter value
                parsed_filter = ListParams._parse_filter_value(field_name, operator, value)
                if parsed_filter is not None:
                    filters[field_name] = parsed_filter
                    
        except Exception as e:
            notify_error(f"Error parsing filter parameter: {str(e)}")
            
        return filters
    
    @staticmethod
    def _parse_filter_value(field_name: str, operator: str, value: str) -> Union[str, int, float, Dict[str, Any], None]:
        """Parse individual filter value based on operator."""
        
        try:
            if operator == "eq":
                # Exact match - try to parse as number, fall back to string
                return ListParams._parse_number(value) if ListParams._parse_number(value) is not None else value
                
            elif operator == "gt":
                num_val = ListParams._parse_number(value)
                if num_val is None:
                    notify_error(f"gt operator requires numeric value for '{field_name}': {value}")
                    return None
                return {"$gt": num_val}
                
            elif operator == "gte":
                num_val = ListParams._parse_number(value)
                if num_val is None:
                    notify_error(f"gte operator requires numeric value for '{field_name}': {value}")
                    return None
                return {"$gte": num_val}
                
            elif operator == "lt":
                num_val = ListParams._parse_number(value)
                if num_val is None:
                    notify_error(f"lt operator requires numeric value for '{field_name}': {value}")
                    return None
                return {"$lt": num_val}
                
            elif operator == "lte":
                num_val = ListParams._parse_number(value)
                if num_val is None:
                    notify_error(f"lte operator requires numeric value for '{field_name}': {value}")
                    return None
                return {"$lte": num_val}
                
            elif operator == "range":
                # Handle range format: [min:max]
                return ListParams._parse_range_value(field_name, value)
                
            else:
                notify_error(f"Unknown filter operator '{operator}' for field '{field_name}'. Supported: eq, gt, gte, lt, lte, range")
                return None
                
        except Exception as e:
            notify_error(f"Error parsing filter '{field_name}:{operator}:{value}': {str(e)}")
            return None
    
    @staticmethod
    def _parse_range_value(field_name: str, value: str) -> Union[Dict[str, Any], None]:
        """Parse range value: [min:max], [min:], [:max]"""
        
        if not (value.startswith('[') and value.endswith(']') and ':' in value):
            notify_error(f"Invalid range format for '{field_name}': {value}. Use [min:max], [min:], or [:max]")
            return None
            
        range_part = value[1:-1]  # Remove brackets
        if range_part.count(':') != 1:
            notify_error(f"Invalid range format for '{field_name}': {value}. Use [min:max], [min:], or [:max]")
            return None
            
        min_val, max_val = range_part.split(':', 1)
        
        range_filter = {}
        if min_val:  # [18:] or [18:65]
            min_num = ListParams._parse_number(min_val)
            if min_num is None:
                notify_error(f"Invalid minimum value in range for '{field_name}': {min_val}")
                return None
            range_filter['$gte'] = min_num
            
        if max_val:  # [:65] or [18:65]
            max_num = ListParams._parse_number(max_val)
            if max_num is None:
                notify_error(f"Invalid maximum value in range for '{field_name}': {max_val}")
                return None
            range_filter['$lte'] = max_num
        
        if not range_filter:
            notify_error(f"Empty range specified for '{field_name}': {value}")
            return None
        
        # Validate range logic
        if '$gte' in range_filter and '$lte' in range_filter:
            if range_filter['$gte'] > range_filter['$lte']:
                notify_error(f"Invalid range for '{field_name}': minimum ({range_filter['$gte']}) > maximum ({range_filter['$lte']})")
                return None
        
        return range_filter

    @staticmethod  
    def _parse_field_value(field_name: str, value: str) -> Union[str, int, float, Dict[str, Any], None]:
        """Parse field filter value, handling ranges and type conversion."""
        
        try:
            # Handle range format: [min:max], [min:], [:max]
            if value.startswith('[') and value.endswith(']') and ':' in value:
                range_part = value[1:-1]  # Remove brackets
                if range_part.count(':') != 1:
                    notify_error(f"Invalid range format for '{field_name}': {value}. Use [min:max], [min:], or [:max]")
                    return None
                    
                min_val, max_val = range_part.split(':', 1)
                
                range_filter = {}
                if min_val:  # [18:] or [18:65]
                    min_num = ListParams._parse_number(min_val)
                    if min_num is None:
                        notify_error(f"Invalid minimum value in range for '{field_name}': {min_val}")
                        return None
                    range_filter['$gte'] = min_num
                    
                if max_val:  # [:65] or [18:65]
                    max_num = ListParams._parse_number(max_val)
                    if max_num is None:
                        notify_error(f"Invalid maximum value in range for '{field_name}': {max_val}")
                        return None
                    range_filter['$lte'] = max_num
                
                if not range_filter:
                    notify_error(f"Empty range specified for '{field_name}': {value}")
                    return None
                
                # Validate range logic
                if '$gte' in range_filter and '$lte' in range_filter:
                    if range_filter['$gte'] > range_filter['$lte']:
                        notify_error(f"Invalid range for '{field_name}': minimum ({range_filter['$gte']}) > maximum ({range_filter['$lte']})")
                        return None
                
                return range_filter
            
            # Try to parse as number for exact matches
            numeric_value = ListParams._parse_number(value)
            return numeric_value if numeric_value is not None else value
            
        except Exception as e:
            notify_error(f"Error parsing filter '{field_name}={value}': {str(e)}")
            return None
    
    @staticmethod
    def _parse_number(value: str) -> Union[int, float, None]:
        """Try to parse string as number, return None if not numeric."""
        try:
            value = value.strip()
            if not value:
                return None
            # Try integer first
            if '.' not in value:
                return int(value)
            else:
                return float(value)
        except (ValueError, TypeError):
            return None
    
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return (f"ListParams(page={self.page}, page_size={self.page_size}, "
                f"sort={self.sort_field}:{self.sort_order}, "
                f"filters={self.filters})")