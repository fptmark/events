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
                else:
                    # All other parameters are field filters
                    parsed_value = cls._parse_field_value(key, value)
                    if parsed_value is not None:
                        params.filters[key] = parsed_value
            except ValueError as e:
                notify_error(f"Invalid parameter '{key}={value}': {str(e)}")
                continue
        
        return params
    
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