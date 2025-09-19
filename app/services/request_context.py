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
from app.services.notify import Notification, Error
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
            Notification.error(Error.REQUEST, f"Invalid URL path: {str(e)}")
        
        # Parse query parameters
        RequestContext._parse_url_query_params(query_params)


    @staticmethod
    def reset():
        """Reset context for new request"""
        RequestContext.entity_type = ""
        RequestContext.entity_metadata = {}
        RequestContext.entity_id = None
        RequestContext.filters = {}
        RequestContext.sort_fields = []
        RequestContext.page = 1
        RequestContext.pageSize = 25
        RequestContext.view_spec = {}

    
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
        RequestContext.entity_metadata = MetadataService.get(RequestContext.entity_type)
        RequestContext.entity_id = entity_id
        
        if not RequestContext.entity_metadata:
            Notification.error(Error.REQUEST, f"Entity metadata not found: {RequestContext.entity_type}")
    
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
        
        # Query params are already normalized to lowercase upstream
        normalized_params = query_params
        
        # Parse each query parameter
        for key, value in normalized_params.items():
            try:
                if key == 'page':
                    try:
                        page_val = int(value)
                        if page_val < 1:
                            Notification.request_warning("Page number must be >= 1. Using page=1", value=value, parameter='page')
                            RequestContext.page = 1
                        else:
                            RequestContext.page = page_val
                    except ValueError:
                        Notification.request_warning("Invalid page number. Using page=1", value=value, parameter='page')
                        RequestContext.page = 1
                        
                elif key == 'pagesize':  # URL param is pageSize but gets lowercased
                    try:
                        size_val = int(value)
                        if size_val < 1:
                            Notification.request_warning("pageSize must be >= 1. Using pageSize=25", value=value, parameter='pageSize')
                            RequestContext.pageSize = 25
                        elif size_val > 1000:
                            Notification.request_warning("pageSize cannot exceed 1000. Using pageSize=1000", value=value, parameter='pageSize')
                            RequestContext.pageSize = 1000
                        else:
                            RequestContext.pageSize = size_val
                    except ValueError:
                        Notification.request_warning("Invalid pageSize. Using pageSize=25", value=value, parameter='pageSize')
                        RequestContext.pageSize = 25
                        
                elif key == 'sort':
                    RequestContext.sort_fields = RequestContext._parse_sort_parameter(value, RequestContext.entity_type)
                    
                elif key == 'filter':
                    RequestContext.filters = RequestContext._parse_filter_parameter(value, RequestContext.entity_type)
                    
                elif key == 'view':
                    RequestContext.view_spec = RequestContext._parse_view_parameter(value, RequestContext.entity_type)
                        
                else:
                    # Unknown parameter - ignore and continue
                    valid_params = ['page', 'pageSize', 'sort', 'filter', 'view']
                    Notification.request_warning("Unknown query parameter. Valid parameters: page, pageSize, sort, filter, view", parameter=key)
                    
            except ValueError as e:
                Notification.request_warning("Invalid parameter value", value=value, parameter=key)
    
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
            else:
                field_name = field_spec
                direction = "asc"
                
            if not field_name:
                Notification.request_warning("Empty field name in sort", value=field_spec, parameter='sort')
                continue

            if not MetadataService.get(entity_name, field_name):
                Notification.request_warning("Unknown sort field", value=field_name, parameter='sort')
                continue
            
            if direction not in ['asc', 'desc']:
                Notification.request_warning("Invalid sort direction. Use 'asc' or 'desc'", value=f"{field_name}:{direction}", parameter='sort')
                direction = 'asc'
            
            # Use lowercase field name - proper casing handled by database driver
            sort_fields.append((field_name, direction))
        
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
                    Notification.request_warning("Invalid filter format. Use field:value", value=filter_part, parameter='filter')
                    continue
                    
                field_name = parts[0].strip()
                if not field_name:
                    Notification.request_warning("Empty field name in filter", value=filter_part, parameter='filter')
                    continue
                
                if not MetadataService.get(entity_name, field_name):
                    Notification.request_warning("Unknown filter field", value=field_name, parameter='filter')
                    continue
                
                if len(parts) == 2:
                    # Simple format: field:value
                    operator = "eq"
                    value = parts[1].strip() 
                else:
                    # Extended format: field:operator:value
                    operator = parts[1].strip().lower()
                    value = parts[2].strip()
                
                # Parse the filter value with type conversion
                parsed_filter = RequestContext._parse_filter_value(entity_name, field_name, operator, value)
                if parsed_filter is not None:
                    # Handle multiple conditions on the same field (e.g., age:gte:21,age:lt:65)
                    if field_name in filters:
                        existing_filter = filters[field_name]
                        if isinstance(existing_filter, dict) and isinstance(parsed_filter, dict):
                            # Merge dictionaries for range conditions like {"$gte": X} + {"$lt": Y}
                            existing_filter.update(parsed_filter)
                        else:
                            # For non-dict filters, overwrite (shouldn't happen with range operators)
                            filters[field_name] = parsed_filter
                    else:
                        filters[field_name] = parsed_filter
                        
        except Exception as e:
            Notification.request_warning("Error parsing filter parameter", parameter='filter')
            
        return filters

    @staticmethod
    def _parse_filter_value(entity_name: str, field_name: str, operator: str, value: str) -> Union[str, int, float, bool, Dict[str, Any], None]:
        """Parse individual filter value based on field type and operator."""
        try:
            # Get field type from metadata for proper type conversion
            field_type = MetadataService.get(entity_name, field_name, 'type')
            
            # Convert value based on field type
            typed_value = RequestContext._convert_value_by_type(entity_name, field_name, value, field_type)
            
            if operator == "eq":
                return typed_value
                
            elif operator == "gt":
                return {"$gt": typed_value}
                
            elif operator == "gte":
                return {"$gte": typed_value}
                
            elif operator == "lt":
                return {"$lt": typed_value}
                
            elif operator == "lte":
                return {"$lte": typed_value}
                
            else:
                Notification.request_warning("Unknown filter operator. Supported: eq, gt, gte, lt, lte", value=f"{field_name}:{operator}", parameter='filter')
                return None
                
        except Exception as e:
            Notification.request_warning("Error parsing filter", value=f"{field_name}:{operator}:{value}", parameter='filter')
            return None
            
        return None  # Should never reach here due to request_error() exceptions

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
                Notification.request_warning("Invalid view format. Use format: fk_name(field1,field2)", value=view_str, parameter='view')
                return {}
            
            for fk_name, fields_str in matches:
                # First validate the foreign entity exists
                if not MetadataService.get(fk_name):
                    Notification.request_warning("Unknown entity in view", entity=fk_name, parameter='view')
                    continue
                
                field_names = []
                for field in fields_str.split(','):
                    field = field.strip()
                    if field:
                        # Check if field exists in the FOREIGN entity, not current entity
                        if not MetadataService.get(fk_name, field):
                            Notification.request_warning("Unknown field in view", entity=fk_name, field=field, parameter='view')
                            continue
                        field_names.append(field)
                
                if field_names:
                    view_spec[fk_name] = field_names
            
            return view_spec if view_spec else {}
            
        except Exception as e:
            Notification.request_warning("Error parsing view parameter", parameter='view')
            return {}
            
        return {}  # Should never reach here due to request_error() exceptions

    @staticmethod
    def _convert_value_by_type(entity_name: str, field_name: str, value: str, field_type: str) -> Union[str, int, float, bool, None]:
        """Convert string value to appropriate type based on field metadata."""
        try:
            value = value.strip()
            if not value:
                return None
                
            # Handle type conversions based on schema types
            if field_type == 'Boolean':
                if value.lower() in ('true', '1', 'yes'):
                    return True
                elif value.lower() in ('false', '0', 'no'):
                    return False
                else:
                    Notification.request_warning("Invalid boolean value. Use true/false", value=f"{field_name}:{value}", parameter='filter')
                    return None
                    
            elif field_type in ('Currency', 'Number'):
                try:
                    return float(value)
                except ValueError:
                    Notification.request_warning(f"Invalid {field_type.lower()} value", value=f"{field_name}:{value}", parameter='filter')
                    return None
                    
            elif field_type == 'Integer':
                try:
                    return int(value)
                except ValueError:
                    Notification.request_warning("Invalid integer value", value=f"{field_name}:{value}", parameter='filter')
                    return None
                    
            elif field_type in ('Date', 'Datetime'):
                # Keep as string - database driver will handle date parsing
                # TODO: Add date validation if needed
                return value
                
            else:
                # String, ObjectId, JSON, Array[String] - keep as string
                return value
                
        except Exception as e:
            Notification.request_warning(f"Error converting {field_type.lower()} value", value=f"{field_name}:{value}", parameter='filter')
            return None
            
        return None  # Should never reach here due to request_error() exceptions
    
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