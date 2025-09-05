"""
RequestContext for managing request parameters and entity context.

This service manages request state and entity context for API operations,
replacing URL-specific logic with generic request context management.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union
from urllib.parse import unquote
from app.services.metadata import MetadataService
from app.services.notification import system_error
from app.utils import parse_url_path


class RequestContext:
    """
    Static service for managing request parameters and entity context.
    Replaces UrlService with cleaner, more generic request context management. 
    """
    
    # Core entity info
    entity_type: str = ""                             # Lowercase entity type for database
    entity_metadata: Dict[str, Any] = {}
    entity_id: Optional[str] = None                   # Document ID from URL path
    
    # Query parameters  
    filters: Dict[str, Any] = {}
    sort_fields: List[Tuple[str, str]] = []
    page: int = 1
    pageSize: int = 25
    
    # View/expansion
    view_spec: Dict[str, Any] = {}
    
    @staticmethod
    def parse_request(path: str, query_params: Dict[str, str]) -> None:
        """
        Parse URL path and query parameters and set RequestContext state.
        
        Args:
            path: URL path like "/api/user/123" or "/api/user"  
            query_params: Query parameters dict from FastAPI request
        """
        # Parse URL path for entity and ID
        try:
            entity_type, entity_id = parse_url_path(path)
            RequestContext.setup_entity(entity_type, entity_id)
            
        except ValueError as e:
            system_error(f"Invalid URL path: {str(e)}")
            return
        
        # Parse query parameters
        RequestContext._parse_url_query_params(query_params)
    
    @staticmethod
    def from_request(request) -> None:
        """
        Parse FastAPI Request object and set RequestContext state.
        
        Args:
            request: FastAPI Request object
        """
        RequestContext.parse_request(str(request.url.path), dict(request.query_params))
    
    @staticmethod
    def setup_entity(
        entity_name: str, 
        entity_id: Optional[str] = None
    ) -> None:
        """
        Setup entity context for operations (programmatic or URL-based).
        
        Args:
            entity_name: Entity name (will be normalized via metadata)
            entity_id: Optional document ID
        """
        # Normalize entity name and get metadata
        RequestContext.entity_type = MetadataService.get_proper_name(entity_name)
        RequestContext.entity_metadata = MetadataService.get(RequestContext.entity_type) or {}
        RequestContext.entity_id = entity_id
        
        if not RequestContext.entity_metadata:
            system_error(f"Entity metadata not found: {RequestContext.entity_type}")
    
    @staticmethod
    def set_parameters(
        page: int = 1,
        pageSize: int = 25,
        filters: Optional[Dict[str, Any]] = None,
        sort_fields: Optional[List[Tuple[str, str]]] = None,
        view_spec: Dict[str, Any] = {}
    ) -> None:
        """
        Set query parameters directly (for programmatic use).
        
        Args:
            page: Page number
            pageSize: Items per page
            filters: Filter conditions dict
            sort_fields: List of (field, direction) tuples
            view_spec: View specification dict
        """
        RequestContext.page = page
        RequestContext.pageSize = pageSize
        RequestContext.filters = filters or {}
        RequestContext.sort_fields = sort_fields or []
        RequestContext.view_spec = view_spec
    
    @staticmethod
    def _parse_url_query_params(query_params: Dict[str, str]) -> None:
        """Parse query parameters and set context attributes."""
        
        # Convert query params to lowercase for case-insensitive handling
        normalized_params = {key.lower(): value for key, value in query_params.items()}
        
        # Parse each query parameter
        for key, value in normalized_params.items():
            try:
                if key == 'page':
                    page_val = int(value)
                    if page_val < 1:
                        system_error(f"Page number must be >= 1, got: {value}")
                        RequestContext.page = 1
                    else:
                        RequestContext.page = page_val
                        
                elif key == 'pagesize':  # URL param is pageSize but gets lowercased
                    size_val = int(value)
                    if size_val < 1:
                        system_error(f"Page size must be >= 1, got: {value}")
                        RequestContext.pageSize = 25
                    elif size_val > 1000:
                        system_error(f"Page size cannot exceed 1000, got: {value}")
                        RequestContext.pageSize = 1000
                    else:
                        RequestContext.pageSize = size_val
                        
                elif key == 'sort':
                    RequestContext.sort_fields = RequestContext._parse_sort_parameter(value, RequestContext.entity_type)
                    
                elif key == 'filter':
                    RequestContext.filters = RequestContext._parse_filter_parameter(value, RequestContext.entity_type)
                    
                elif key == 'view':
                    RequestContext.view_spec = RequestContext._parse_view_parameter(value, RequestContext.entity_type)
                        
                else:
                    # Unknown parameter
                    valid_params = ['page', 'pageSize', 'sort', 'filter', 'view']
                    system_error(f"Invalid query parameter '{key}'. Valid parameters: {', '.join(valid_params)}")
                    
            except ValueError as e:
                system_error(f"Invalid parameter '{key}={value}': {str(e)}")
                continue
    
    @staticmethod
    def to_dict() -> Dict[str, Any]:
        """Convert RequestContext to dictionary for serialization/debugging."""
        return {
            'entity_type': RequestContext.entity_type,
            'entity_id': RequestContext.entity_id,
            'filters': RequestContext.filters,
            'sort_fields': RequestContext.sort_fields,
            'page': RequestContext.page,
            'pageSize': RequestContext.pageSize,
            'view_spec': RequestContext.view_spec,
            'has_metadata': bool(RequestContext.entity_metadata)
        }
    
    @staticmethod
    def get_debug_string() -> str:
        """String representation for debugging."""
        return f"RequestContext(entity={RequestContext.entity_type}, id={RequestContext.entity_id}, page={RequestContext.page}/{RequestContext.pageSize})"
    
    @staticmethod
    def _parse_sort_parameter(sort_str: str, entity_name: str) -> List[Tuple[str, str]]:
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
                    system_error(f"Empty field name in sort: '{field_spec}'")
                    continue
                
                if direction not in ['asc', 'desc']:
                    system_error(f"Invalid sort direction '{direction}' for field '{field_name}'. Use 'asc' or 'desc'")
                    continue
                
                # Map field name to proper case using MetadataService
                proper_field_name = MetadataService.get_proper_name(entity_name, field_name)
                sort_fields.append((proper_field_name, direction))
                
            else:
                # No direction specified - default to ascending
                proper_field_name = MetadataService.get_proper_name(entity_name, field_spec)
                sort_fields.append((proper_field_name, "asc"))
        
        return sort_fields

    @staticmethod
    def _parse_filter_parameter(filter_str: str, entity_name: str) -> Dict[str, Any]:
        """
        Parse filter parameter string into filters dict.
        
        Args:
            filter_str: Filter parameter like "lastName:Smith,age:gte:21,age:lt:65"
            entity_name: Entity name for field name resolution
            
        Returns:
            Dict like {"lastName": "Smith", "age": {"$gte": 21, "$lt": 65}}
        """
        filters: Dict[str, Any] = {}
        
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
                    system_error(f"Invalid filter format: '{filter_part}'. Use field:value")
                    continue
                    
                field_name = parts[0].strip()
                if not field_name:
                    system_error(f"Empty field name in filter: '{filter_part}'")
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
                parsed_filter = RequestContext._parse_filter_value(proper_field_name, operator, value)
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
            system_error(f"Error parsing filter parameter: {str(e)}")
            
        return filters

    @staticmethod
    def _parse_filter_value(field_name: str, operator: str, value: str) -> Union[str, int, float, Dict[str, Any], None]:
        """Parse individual filter value based on operator."""
        try:
            if operator == "eq":
                # Exact match - try to parse as number, fall back to string
                return RequestContext._parse_number(value) if RequestContext._parse_number(value) is not None else value
                
            elif operator == "gt":
                # Try to parse as number first, but allow non-numeric values (like dates)
                num_val = RequestContext._parse_number(value)
                return {"$gt": num_val if num_val is not None else value}
                
            elif operator == "gte":
                # Try to parse as number first, but allow non-numeric values (like dates)
                num_val = RequestContext._parse_number(value)
                return {"$gte": num_val if num_val is not None else value}
                
            elif operator == "lt":
                # Try to parse as number first, but allow non-numeric values (like dates)
                num_val = RequestContext._parse_number(value)
                return {"$lt": num_val if num_val is not None else value}
                
            elif operator == "lte":
                # Try to parse as number first, but allow non-numeric values (like dates)
                num_val = RequestContext._parse_number(value)
                return {"$lte": num_val if num_val is not None else value}
                
            else:
                system_error(f"Unknown filter operator '{operator}' for field '{field_name}'. Supported: eq, gt, gte, lt, lte")
                return None
                
        except Exception as e:
            system_error(f"Error parsing filter '{field_name}:{operator}:{value}': {str(e)}")
            return None

    @staticmethod
    def _parse_view_parameter(view_str: str, entity_name: str) -> Dict[str, List[str]]:
        """
        Parse view parameter into FK expansion dict.
        
        Args:
            view_str: View parameter like "account(id,name),profile(firstName,lastName)"
            entity_name: Entity name for field name resolution
            
        Returns:
            Dict like {"account": ["id", "name"], "profile": ["firstName", "lastName"]}
        """
        if not view_str or view_str.strip() == "":
            return {}
        
        view_spec = {}
        
        try:
            import re
            
            # Regex to match fk_name(field1,field2,field3) patterns
            pattern = r'(\w+)\(([^)]+)\)'
            matches = re.findall(pattern, view_str)
            
            if not matches:
                system_error(f"Invalid view format: '{view_str}'. Use format: fk_name(field1,field2)")
                return {}
            
            for fk_name, fields_str in matches:
                field_names = []
                for field in fields_str.split(','):
                    field = field.strip()
                    if field:
                        # Map field name to proper case using MetadataService
                        proper_field_name = MetadataService.get_proper_name(entity_name, field)
                        field_names.append(proper_field_name)
                
                if field_names:
                    view_spec[fk_name] = field_names
            
            return view_spec if view_spec else {}
            
        except Exception as e:
            system_error(f"Error parsing view parameter: {str(e)}")
            return {}

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