"""
RequestContext for managing request parameters and entity context.

This service manages request state and entity context for API operations,
replacing URL-specific logic with generic request context management.

Uses contextvars for async-safe, request-scoped state management.
"""

import json
import re
from contextvars import ContextVar
from typing import Optional, Dict, Any, List, Tuple, Union
from app.core.metadata import MetadataService
from app.core.notify import Notification, HTTP
from app.core.utils import parse_url_path


# Context variables for request-scoped state (async-safe)
_entity: ContextVar[str] = ContextVar('entity', default="")
_entity_metadata: ContextVar[Dict[str, Any]] = ContextVar('entity_metadata', default={})
_entity_id: ContextVar[Optional[str]] = ContextVar('entity_id', default=None)
_filters: ContextVar[Dict[str, Any]] = ContextVar('filters', default={})
_sort_fields: ContextVar[List[Tuple[str, str]]] = ContextVar('sort_fields', default=[])
_page: ContextVar[int] = ContextVar('page', default=1)
_pageSize: ContextVar[int] = ContextVar('pageSize', default=25)
_view_spec: ContextVar[Dict[str, Any]] = ContextVar('view_spec', default={})
_substring_match: ContextVar[bool] = ContextVar('substring_match', default=True)
_no_consistency: ContextVar[bool] = ContextVar('no_consistency', default=False)
_session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


class RequestContext:
    """
    Service for managing request parameters and entity context using contextvars.
    Provides async-safe, request-scoped state management for API operations.
    """

    # Property accessors for context variables
    @staticmethod
    def get_entity() -> str:
        return _entity.get()

    @staticmethod
    def get_entity_metadata() -> Dict[str, Any]:
        return _entity_metadata.get()

    @staticmethod
    def get_entity_id() -> Optional[str]:
        return _entity_id.get()

    @staticmethod
    def get_filters() -> Dict[str, Any]:
        return _filters.get()

    @staticmethod
    def get_sort_fields() -> List[Tuple[str, str]]:
        return _sort_fields.get()

    @staticmethod
    def get_page() -> int:
        return _page.get()

    @staticmethod
    def get_pageSize() -> int:
        return _pageSize.get()

    @staticmethod
    def get_view_spec() -> Dict[str, Any]:
        return _view_spec.get()

    @staticmethod
    def get_substring_match() -> bool:
        return _substring_match.get()

    @staticmethod
    def get_no_consistency() -> bool:
        return _no_consistency.get()

    @staticmethod
    def get_session_id() -> Optional[str]:
        """Get session ID from request context"""
        return _session_id.get()

    @staticmethod
    def set_session_id(session_id: Optional[str]) -> None:
        """Set session ID in request context"""
        _session_id.set(session_id)

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
            entity, entity_id = parse_url_path(path)
            RequestContext.setup_entity(entity, entity_id)
            
        except ValueError as e:
            Notification.error(HTTP.BAD_REQUEST, f"Invalid URL path: {str(e)}")
        
        # Parse query parameters
        RequestContext._parse_url_query_params(query_params)


    @staticmethod
    def reset():
        """Reset context for new request"""
        _entity.set("")
        _entity_metadata.set({})
        _entity_id.set(None)
        _filters.set({})
        _sort_fields.set([])
        _page.set(1)
        _pageSize.set(25)
        _view_spec.set({})
        _substring_match.set(True)
        _no_consistency.set(False)
        _session_id.set(None)

    
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
        entity: str,
        entity_id: Optional[str] = None
    ) -> None:
        """
        Setup entity context for operations (programmatic or URL-based).

        Args:
            entity: Entity name (will be normalized via metadata)
            entity_id: Optional document ID
        """
        # Normalize entity name and get metadata
        entity_name = MetadataService.get_proper_name(entity)
        entity_metadata = MetadataService.get(entity_name)

        _entity.set(entity_name)
        _entity_metadata.set(entity_metadata)
        _entity_id.set(entity_id)

        if not entity_metadata:
            Notification.error(HTTP.BAD_REQUEST, f"Entity metadata not found: {entity_name}")
    
    @staticmethod
    def set_parameters(
        page: int = 1,
        pageSize: int = 25,
        filters: Optional[Dict[str, Any]] = None,
        substring_match: bool = True,
        sort_fields: Optional[List[Tuple[str, str]]] = None,
        view_spec: Dict[str, Any] = {}
    ) -> None:
        """
        Set query parameters directly (for programmatic use).

        Args:
            page: Page number
            pageSize: Items per page
            filters: Filter conditions dict
            substring_match: True for substring matching (default), False for full string matching
            sort_fields: List of (field, direction) tuples
            view_spec: View specification dict
        """
        _page.set(page)
        _pageSize.set(pageSize)
        _filters.set(filters or {})
        _substring_match.set(substring_match)
        _sort_fields.set(sort_fields or [])
        _view_spec.set(view_spec)
    
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
                            Notification.error(HTTP.BAD_REQUEST, f"Page Number must be >= 1. Page={value}")
                    except ValueError:
                        Notification.error(HTTP.BAD_REQUEST, f"Bad Page Number {value}")
                    _page.set(page_val)

                elif key == 'pagesize':  # URL param is pageSize but gets lowercased
                    try:
                        size_val = int(value)
                        if size_val < 1:
                            Notification.error(HTTP.BAD_REQUEST, f"Page Size must be >= 1. PageSize={value}")
                        elif size_val > 1000:
                            Notification.error(HTTP.BAD_REQUEST, f"Page Size must be < 1000. PageSize={value}")
                    except ValueError:
                        Notification.error(HTTP.BAD_REQUEST, f"Bad Page Size {value}")
                    _pageSize.set(size_val)

                elif key == 'sort':
                    _sort_fields.set(RequestContext._parse_sort_parameter(value, _entity.get()))

                elif key == 'filter':
                    _filters.set(RequestContext._parse_filter_parameter(value, _entity.get()))

                elif key == 'full_match':
                    # Presence of full_match parameter means exact matching (substring_match=False)
                    # Absence means substring matching (substring_match=True, default)
                    _substring_match.set(False)

                elif key == 'view':
                    _view_spec.set(RequestContext._parse_view_parameter(value, _entity.get()))

                # elif key == 'novalidate':
                #     RequestContext.novalidate = True

                elif key == 'no_consistency':
                    _no_consistency.set(value.lower() in ('true', '1', 'yes'))

                else:
                    # Unknown parameter - ignore and continue
                    valid_params = ['page', 'pageSize', 'sort', 'filter', 'view', 'no_consistency', 'full_match']
                    Notification.error(HTTP.BAD_REQUEST, f"Unknown query parameter={key}. Valid parameters: {', '.join(valid_params)}")
                    
            except ValueError as e:
                Notification.error(HTTP.BAD_REQUEST, f"Invalid parameter valuee={value}")
    
    @staticmethod
    def to_dict() -> Dict[str, Any]:
        """Convert RequestContext to dictionary for serialization/debugging."""
        return {
            'entity': _entity.get(),
            'entity_id': _entity_id.get(),
            'filters': _filters.get(),
            'substring_match': _substring_match.get(),
            'sort_fields': _sort_fields.get(),
            'page': _page.get(),
            'pageSize': _pageSize.get(),
            'view_spec': _view_spec.get(),
            'has_metadata': bool(_entity_metadata.get()),
            'session_id': _session_id.get()
        }

    @staticmethod
    def get_debug_string() -> str:
        """String representation for debugging."""
        return f"RequestContext(entity={_entity.get()}, id={_entity_id.get()}, page={_page.get()}/{_pageSize.get()})"
    
    @staticmethod
    def _parse_sort_parameter(sort_str: str, entity: str) -> List[Tuple[str, str]]:
        """
        Parse sort parameter into list of properly-cased sort field tuples.
        
        Args:
            sort_str: Sort parameter like "firstName:desc,lastName:asc"
            entity: Entity name for field name resolution
            
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
                field = parts[0].strip()
                direction = parts[1].strip().lower()
            else:
                field = field_spec
                direction = "asc"
                
            if not field:
                Notification.error(HTTP.BAD_REQUEST, "Empty field name in sort", entity=entity)

            if not MetadataService.get(entity, field):
                Notification.error(HTTP.BAD_REQUEST, f"Unknown sort field", entity=entity, field=field)

            if direction not in ['asc', 'desc']:
                Notification.error(HTTP.BAD_REQUEST, f"Invalid sort direction. Use 'asc' or 'desc'", entity=entity, field=field)
            
            # Use lowercase field name - proper casing handled by database driver
            sort_fields.append((field, direction))
        
        return sort_fields


    @staticmethod
    def _parse_filter_parameter(filter_str: str, entity: str) -> Dict[str, Any]:
        """
        Parse filter parameter string into filters dict.
        
        Args:
            filter_str: Filter parameter like "lastName:Smith,age:gte:21,age:lt:65"
            entity: Entity name for field name resolution
            
        Returns:
            Dict like {"lastName": "Smith", "age": {"$gte": 21, "$lt": 65}}
        """
        filters: Dict[str, Any] = {}
        operators = ['eq', 'ne', 'lt', 'le', 'lte', 'gt', 'ge', 'gte']
        
        if not filter_str or not filter_str.strip():
            return filters
            
        # Split by comma for multiple filters
        for filter_part in filter_str.split(','):
            filter_part = filter_part.strip()
            if not filter_part:
                continue

            # *** split filter_part into array from field:value or field:operator:value
            # if there is a valid quoted string, get it
            m = re.search(r'[:](["\'])([^"\']*)\1$', filter_part)
            if m:
                parts = filter_part[:m.start()].split(':', 2) # split everything up to match
                # quote_char = m.group(1)
                parts.append(m.group(2))    # add cleaned match
            else:   # no balanced quotes - assume any quote marks are escaped properly.  if not, too bad!
                parts = filter_part.split(':')

            if len(parts) < 2:
                Notification.error(HTTP.BAD_REQUEST, f"Invalid filter format. Use field:value instead of {filter_part}")

            field = parts[0].strip()
            if not MetadataService.get(entity, field):
                Notification.error(HTTP.BAD_REQUEST, f"Invalid filter field", entity=entity, field=field)

            if len(parts) > 2:
                operator, value = parts[1].strip(), parts[2]
            else:
                operator, value = 'eq', parts[1]

            if operator not in operators:
                Notification.error(HTTP.BAD_REQUEST, f"Unknown operator={operator}")

            value = value.strip()
            if len(value) == 0:
                Notification.error(HTTP.BAD_REQUEST, f"Missing filter value in {filter_part}")

            # Parse the filter value with type conversion
            parsed_filter = RequestContext._parse_filter_value(entity, field, operator, value)
            if parsed_filter is not None:
                # Handle multiple conditions on the same field (e.g., age:gte:21,age:lt:65)
                if field in filters:
                    existing_filter = filters[field]
                    if isinstance(existing_filter, dict) and isinstance(parsed_filter, dict):
                        # Merge dictionaries for range conditions like {"$gte": X} + {"$lt": Y}
                        existing_filter.update(parsed_filter)
                    else:
                        # For non-dict filters, overwrite (shouldn't happen with range operators)
                        filters[field] = parsed_filter
                else:
                    filters[field] = parsed_filter
                        
        return filters

    @staticmethod
    def _parse_filter_value(entity: str, field: str, operator: str, value: str) -> Union[str, int, float, bool, Dict[str, Any], None]:
        """Parse individual filter value based on field type and operator."""
        try:
            # Get field type from metadata for proper type conversion
            field_type = MetadataService.get(entity, field, 'type')
            
            # Convert value based on field type
            typed_value = RequestContext._convert_value_by_type(entity, field, value, field_type)
            
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
                Notification.request_warning("Unknown filter operator. Supported: eq, gt, gte, lt, lte", value=f"{field}:{operator}", parameter='filter')
                return None
                
        except Exception as e:
            Notification.request_warning("Error parsing filter", value=f"{field}:{operator}:{value}", parameter='filter')
            return None
            
        return None  # Should never reach here due to request_error() exceptions

    @staticmethod
    def _parse_view_parameter(view_str: str, entity: str) -> Dict[str, List[str]]:
        """
        Parse view parameter into FK expansion dict.
        
        Args:
            view_str: View parameter like "account(id,name),profile(firstName,lastName)"
            entity: Entity name for field name resolution
            
        Returns:
            Dict like {"account": ["id", "name"], "profile": ["firstName", "lastName"]}
        """
        if not view_str or view_str.strip() == "":
            return {}
        
        view_spec = {}
        
        import re
        
        # Regex to match fk_name(field1,field2,field3) patterns
        pattern = r'(\w+)\(([^)]+)\)'
        matches = re.findall(pattern, view_str)
        
        if not matches:
            Notification.error(HTTP.BAD_REQUEST, f"Invalid view format={view_str}. Use format: fk_name(field1,field2)")
            return {}
        
        for fk_name, fields_str in matches:
            # First validate the foreign entity exists
            if not MetadataService.get(fk_name):
                Notification.error(HTTP.BAD_REQUEST, f"Unknown entity={fk_name} in view")
                continue
            
            fields = []
            for field in fields_str.split(','):
                field = field.strip()
                if field:
                    # Check if field exists in the FOREIGN entity, not current entity
                    if not MetadataService.get(fk_name, field):
                        Notification.error(HTTP.BAD_REQUEST, f"Unknown field={fk_name}.{field} in view")
                    fields.append(field)
            
            if fields:
                view_spec[fk_name] = fields
        
        return view_spec if view_spec else {}
            
        return {}  # Should never reach here due to request_error() exceptions

    @staticmethod
    def _convert_value_by_type(entity: str, field: str, value: str, field_type: str) -> Union[str, int, float, bool, None]:
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
                    Notification.request_warning("Invalid boolean value. Use true/false", value=f"{field}:{value}", parameter='filter')
                    return None
                    
            elif field_type in ('Currency', 'Number'):
                try:
                    return float(value)
                except ValueError:
                    Notification.request_warning(f"Invalid {field_type.lower()} value", value=f"{field}:{value}", parameter='filter')
                    return None
                    
            elif field_type == 'Integer':
                try:
                    return int(value)
                except ValueError:
                    Notification.request_warning("Invalid integer value", value=f"{field}:{value}", parameter='filter')
                    return None
                    
            elif field_type in ('Date', 'Datetime'):
                # Keep as string - database driver will handle date parsing
                # TODO: Add date validation if needed
                return value
                
            else:
                # String, ObjectId, JSON, Array[String] - keep as string
                return value
                
        except Exception as e:
            Notification.request_warning(f"Error converting {field_type.lower()} value", value=f"{field}:{value}", parameter='filter')
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