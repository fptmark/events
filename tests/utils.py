def get_model_class(entity_name: str) -> type:
    """Get model class dynamically by entity name using introspection"""
    import importlib
    import inspect
    
    # Convert entity name to expected module/class naming convention
    # e.g., 'User' -> 'user_model' and 'User', 'TagAffinity' -> 'tagaffinity_model' and 'TagAffinity'
    module_name = f"{entity_name.lower()}_model"
    
    try:
        # Try to import the module
        module = importlib.import_module(f"app.models.{module_name}")
        
        # Look for a class with the exact entity name (case-sensitive)
        if hasattr(module, entity_name.capitalize()):
            model_class = getattr(module, entity_name.capitalize())
            # Verify it's actually a class and has get_metadata method
            if inspect.isclass(model_class) and hasattr(model_class, 'get_metadata'):
                return model_class
        
        # Fallback: look for any class in the module that has get_metadata
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if hasattr(obj, 'get_metadata') and obj.__module__ == module.__name__:
                return obj
        
        # If we get here, no suitable class was found
        raise ValueError(f"No model class with get_metadata method found in {module_name} for entity '{entity_name}'")
        
    except ImportError as e:
        raise ImportError(f"Could not import module app.models.{module_name} for entity '{entity_name}'") from e 

def get_fk_entity(field_name: str) -> str | None:
    if len(field_name) > 2 and field_name.endswith("id"):
        return field_name[2:]
    else:
        return None 

def get_url_fields(url: str):
    """Extract field names from URL parameters.
    
    Returns:
        List of field names found in sort, filter, and view parameters
    """
    import urllib.parse as urlparse
    import json
    from typing import List
    
    fields = []
    
    # Parse the URL to get query parameters
    parsed_url = urlparse.urlparse(url)
    parsed_params = urlparse.parse_qs(parsed_url.query)
    
    # Extract fields from sort parameters
    sort_values = parsed_params.get('sort', [])
    for sort_param in sort_values:
        # Handle comma-separated sort fields
        sort_fields = [f.strip() for f in sort_param.split(',')]
        for field in sort_fields:
            # Remove leading - for descending sort
            clean_field = field.lstrip('-').strip()
            if clean_field:
                fields.append(clean_field)
    
    # Extract fields from filter parameters  
    filter_values = parsed_params.get('filter', [])
    for filter_param in filter_values:
        # Handle comma-separated filter conditions
        filter_conditions = [f.strip() for f in filter_param.split(',')]
        for condition in filter_conditions:
            # Parse field:value or field:operator:value format
            parts = condition.split(':')
            if len(parts) >= 2:
                field_name = parts[0].strip()
                if field_name:
                    fields.append(field_name)
    
    # Extract fields from view parameters (JSON format)
    view_values = parsed_params.get('view', [])
    for view_param in view_values:
        try:
            # Decode URL-encoded JSON
            decoded_view = urlparse.unquote(view_param)
            view_spec = json.loads(decoded_view)
            
            # view format: {"entity": ["field1", "field2"], ...}
            for entity_name, field_list in view_spec.items():
                if isinstance(field_list, list):
                    for field_name in field_list:
                        if isinstance(field_name, str) and field_name.strip():
                            # Note: view fields are for FK entities, might need validation
                            fields.append(field_name.strip())
        except (json.JSONDecodeError, ValueError):
            # Ignore malformed view parameters
            pass
    
    return fields