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
