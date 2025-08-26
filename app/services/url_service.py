"""
UrlService for centralized URL parsing and metadata normalization.

This service parses raw URLs into normalized, properly-cased components using 
a single metadata lookup, eliminating the need for scattered metadata calls
throughout the application.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Union
from urllib.parse import unquote
from app.services.metadata import MetadataService
from app.notification import notify_error


class UrlService:
    """Normalized URL components with proper casing from metadata."""
    
    # Core components (properly cased from metadata)
    entity_name: str                              # "Proper" entity name
    entity_metadata: Dict[str, Any] = field(default_factory=dict)
    entity_id: Optional[str] = None               # "123"
    
    # Pagination (URL parameter names)
    page: int = 1
    pageSize: int = 25                           # Match URL param name exactly
    
    # Sort fields (field names properly cased from metadata)
    sort_fields: List[tuple[str, str]] = field(default_factory=list)  # [(field, order), ...]
    
    # Filters (field names properly cased, structure supports ranges like original ListParams)
    filters: Dict[str, Any] = field(default_factory=dict)   # field=value or field={"$gte": X, "$lt": Y}
    
    # View spec (parsed)
    view_spec: Optional[Dict[str, Any]] = None
    
    """Service for parsing and normalizing URL components."""
    @staticmethod
    def parse_request(path: str, query_params: Dict[str, str]) -> None:
        """
        Parse FastAPI request path and query parameters and store in service.
        
        Args:
            path: URL path like "/api/user/123" or "/api/user"  
            query_params: Query parameters dict
        """
        UrlService._parse_path(path.lower())
        UrlService.entity_metadata = MetadataService.get(UrlService.entity_name)  # Validates entity exists
        if UrlService.entity_metadata is None:
            notify_error(f"Entity metadata not found: {UrlService.entity_name}")
        
        # Convert query params to lowercase for case-insensitive handling
        normalized_params = {key.lower(): value for key, value in query_params.items()}
        
        # Parse each query parameter
        for key, value in normalized_params.items():
            try:
                if key == 'page':
                    page_val = int(value)
                    if page_val < 1:
                        notify_error(f"Page number must be >= 1, got: {value}")
                        UrlService.page = 1
                    else:
                        UrlService.page = page_val
                        
                elif key == 'pagesize':  # URL param is pageSize but gets lowercased
                    size_val = int(value)
                    if size_val < 1:
                        notify_error(f"Page size must be >= 1, got: {value}")
                        UrlService.pageSize = 25
                    elif size_val > 1000:
                        notify_error(f"Page size cannot exceed 1000, got: {value}")
                        UrlService.pageSize = 1000
                    else:
                        UrlService.pageSize = size_val
                        
                elif key == 'sort':
                    UrlService.sort_fields = UrlService._parse_sort_parameter(value, UrlService.entity_name)
                    
                elif key == 'filter':
                    UrlService.sort_fields = UrlService._parse_sort_parameter(value, UrlService.entity_name)
                    
                elif key == 'view':
                    try:
                        UrlService.view_spec = json.loads(unquote(value))
                    except (json.JSONDecodeError, ValueError) as e:
                        notify_error(f"Invalid view parameter: {str(e)}")
                        UrlService.view_spec = None
                        
                else:
                    # Unknown parameter
                    valid_params = ['page', 'pageSize', 'sort', 'filter', 'view']
                    notify_error(f"Invalid query parameter '{key}'. Valid parameters: {', '.join(valid_params)}")
                    
            except ValueError as e:
                notify_error(f"Invalid parameter '{key}={value}': {str(e)}")
                continue
        
    
    @staticmethod
    def _parse_path(path: str):
        """
        Extract entity name and entity ID from URL path.
        
        Args:
            path: URL path like "/api/user/123" or "/api/user"
            
        Returns:
            Tuple of (entity_name, entity_id)
        """
        # Remove leading/trailing slashes and split
        path_parts = [part for part in path.strip('/').split('/') if part]
        
        if not path_parts:
            raise ValueError("Empty URL path")
        
        if path_parts[0] != 'api':
            raise ValueError("Missing /api prefix in URL path")
        
        if len(path_parts) < 2:
            raise ValueError("Bad URL format, expected /api/{entity}/{id?}")
        
        entity_name = path_parts[1]  # Entity name after /api
        UrlService.entity_name = MetadataService.get_proper_name(entity_name)  # Normalize entity metadata casing
        UrlService.entity_id = path_parts[2] if len(path_parts) > 2 else None
        
    
    @classmethod
    def _parse_sort_parameter(cls, sort_str: str, entity_name: str) -> List[tuple[str, str]]:
        """
        Parse sort parameter into list of properly-cased sort field tuples.
        
        Args:
            sort_str: Sort parameter like "firstName:desc,lastName:asc"
            entity_name: Entity name for field name resolution
            
        Returns:
            List of tuples like [("firstName", "desc"), ("lastName", "asc")]
        """
        if not sort_str or sort_str.strip() == "":
            return []
        
        sort_fields = []
        for field_spec in sort_str.split(','):
            field_spec = field_spec.strip()
            if not field_spec:
                continue
            
            # Check for field:direction format
            if ':' in field_spec:
                parts = field_spec.split(':', 1)
                field_name = parts[0].strip()
                direction = parts[1].strip().lower()
                
                if not field_name:
                    notify_error(f"Empty field name in sort: '{field_spec}'")
                    continue
                
                if direction not in ['asc', 'desc']:
                    notify_error(f"Invalid sort direction '{direction}' for field '{field_name}'. Use 'asc' or 'desc'")
                    continue
                
                # Map field name to proper case using MetadataService
                proper_field_name = MetadataService.get_proper_name(entity_name, field_name)
                sort_fields.append((proper_field_name, direction))
                
            else:
                # No direction specified - default to ascending
                proper_field_name = MetadataService.get_proper_name(entity_name, field_spec)
                sort_fields.append((proper_field_name, "asc"))
        
        return sort_fields
    
    @classmethod
    def _parse_filter_parameter(cls, filter_str: str, entity_name: str) -> Dict[str, Any]:
        """
        Parse filter parameter string into filters dict (like original ListParams).
        
        Args:
            filter_str: Filter parameter like "lastName:Smith,age:gte:21,age:lt:65"
            entity_name: Entity name for field name resolution
            
        Returns:
            Dict like {"lastName": "Smith", "age": {"$gte": 21, "$lt": 65}}
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
                
                # Map field name to proper case using MetadataService
                proper_field_name = MetadataService.get_proper_name(entity_name, field_name)
                
                if len(parts) == 2:
                    # Simple format: field:value
                    operator = "eq"
                    value = parts[1].strip()
                else:
                    # Extended format: field:operator:value
                    operator = parts[1].strip().lower()
                    value = parts[2].strip()
                
                # Parse the filter value
                parsed_filter = cls._parse_filter_value(proper_field_name, operator, value)
                if parsed_filter is not None:
                    # Handle multiple conditions on the same field (e.g., age:gte:21,age:lt:65)
                    if proper_field_name in filters:
                        existing_filter = filters[proper_field_name]
                        if isinstance(existing_filter, dict) and isinstance(parsed_filter, dict):
                            # Merge dictionaries for range conditions like {"$gte": X} + {"$lt": Y}
                            existing_filter.update(parsed_filter)
                        else:
                            # For non-dict filters, overwrite (shouldn't happen with range operators)
                            filters[proper_field_name] = parsed_filter
                    else:
                        filters[proper_field_name] = parsed_filter
                    
        except Exception as e:
            notify_error(f"Error parsing filter parameter: {str(e)}")
            
        return filters
    
    @classmethod
    def _parse_filter_value(cls, field_name: str, operator: str, value: str) -> Union[str, int, float, Dict[str, Any], None]:
        """Parse individual filter value based on operator (matches original ListParams)."""
        
        try:
            if operator == "eq":
                # Exact match - try to parse as number, fall back to string
                return cls._parse_number(value) if cls._parse_number(value) is not None else value
                
            elif operator == "gt":
                # Try to parse as number first, but allow non-numeric values (like dates)
                num_val = cls._parse_number(value)
                return {"$gt": num_val if num_val is not None else value}
                
            elif operator == "gte":
                # Try to parse as number first, but allow non-numeric values (like dates)
                num_val = cls._parse_number(value)
                return {"$gte": num_val if num_val is not None else value}
                
            elif operator == "lt":
                # Try to parse as number first, but allow non-numeric values (like dates)
                num_val = cls._parse_number(value)
                return {"$lt": num_val if num_val is not None else value}
                
            elif operator == "lte":
                # Try to parse as number first, but allow non-numeric values (like dates)
                num_val = cls._parse_number(value)
                return {"$lte": num_val if num_val is not None else value}
                
            else:
                notify_error(f"Unknown filter operator '{operator}' for field '{field_name}'. Supported: eq, gt, gte, lt, lte")
                return None
                
        except Exception as e:
            notify_error(f"Error parsing filter '{field_name}:{operator}:{value}': {str(e)}")
            return None
    
    @classmethod
    def _parse_number(cls, value: str) -> Union[int, float, None]:
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