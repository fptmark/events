from typing import List, Dict, Any, Optional
from pydantic import ValidationError as PydanticValidationError
import warnings as python_warnings
from app.config import Config
from app.notification import notify_warning, NotificationType

def process_raw_results(cls, entity_type: str, raw_docs: List[Dict[str, Any]], warnings: List[str]) -> List[Dict[str, Any]]:
    """Common processing for raw database results."""
    get_validations, _ = Config.validations(True)
    entities = []

    # ALWAYS validate model data against Pydantic schema (enum, range, string validation, etc.)
    # This is independent of GV settings which only control FK validation
    for doc in raw_docs:
        entities.append(validate_with_notifications(cls, doc, entity_type))  

    # Add database warnings
    for warning in warnings:
        notify_warning(warning, NotificationType.DATABASE)

    # Convert models to dictionaries for FastAPI response validation
    entity_data = []
    for entity in entities:
        with python_warnings.catch_warnings(record=True) as caught_warnings:
            python_warnings.simplefilter("always")
            data_dict = entity.model_dump()
            entity_data.append(data_dict)
            
            # Add any serialization warnings as notifications
            if caught_warnings:
                entity_id = data_dict.get('id')
                if not entity_id:
                    notify_warning("Document missing ID field", NotificationType.DATABASE)
                    entity_id = "missing"

                datetime_field_names = []
                
                # Use the model's metadata to find datetime fields
                for field_name, field_meta in cls._metadata.get('fields', {}).items():
                    if field_meta.get('type') == 'ISODate':
                        if field_name in data_dict and isinstance(data_dict[field_name], str):
                            datetime_field_names.append(field_name)
                
                if datetime_field_names:
                    field_list = ', '.join(datetime_field_names)
                    notify_warning(f"{field_list} datetime serialization warnings", NotificationType.VALIDATION, entity=entity_type, entity_id=entity_id)
                else:
                    # Fallback for non-datetime warnings
                    warning_count = len(caught_warnings)
                    notify_warning(f"{entity_type} {entity_id}: {warning_count} serialization warnings", NotificationType.VALIDATION, entity=entity_type)

    return entity_data


async def validate_objectid_references(entity_name: str, data: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    """
    Generic ObjectId reference validation for any entity.
    
    Args:
        entity_name: Name of the entity being validated (e.g., "User")
        data: Entity data dictionary to validate
        metadata: Entity metadata containing field definitions
    
    Raises:
        ValidationError: If any ObjectId references don't exist
    """
    from app.errors import ValidationError, ValidationFailure, NotFoundError
    from app.routers.router_factory import ModelImportCache
    
    validation_failures = []
    
    # Check all ObjectId fields in the entity metadata
    for field_name, field_meta in metadata.get('fields', {}).items():
        if field_meta.get('type') == 'ObjectId' and data.get(field_name):
            try:
                # Derive FK entity name from field name (e.g., accountId -> Account)
                fk_entity_name = field_name[:-2].capitalize()  # Remove 'Id' suffix and capitalize
                fk_entity_cls = ModelImportCache.get_model_class(fk_entity_name)
                await fk_entity_cls.get(data[field_name])
            except NotFoundError:
                validation_failures.append(ValidationFailure(
                    field_name=field_name,
                    message=f"Id {data[field_name]} does not exist",
                    value=data[field_name]
                ))
            except ImportError:
                # FK entity class doesn't exist - skip validation
                pass
    
    # Raise ValidationError if any ObjectId references are invalid
    if validation_failures:
        raise ValidationError(
            message="Invalid ObjectId references",
            entity=entity_name,
            invalid_fields=validation_failures
        )


# should_process_fk_fields function removed - logic moved directly to models




async def process_entity_fks(entity_dict: Dict[str, Any], view_spec: Optional[Dict[str, Any]], 
                           entity_name: str, entity_cls, fk_validations: bool) -> None:
    """
    Process FK fields for an entity - called exactly once per entity.
    
    Args:
        entity_dict: Entity data dictionary
        view_spec: Dict of FK fields to populate, or None for exists flags only
        entity_name: Name of the entity type
        entity_cls: Entity model class
    """
    from app.routers.router_factory import ModelImportCache
    from app.errors import NotFoundError
    from app.notification import notify_warning, NotificationType
    import re
    
    metadata = entity_cls._metadata
    entity_id = entity_dict.get('id', 'unknown')
    
    for field_name, field_meta in metadata.get('fields', {}).items():
        if field_meta.get('type') == 'ObjectId' and entity_dict.get(field_name):
            fk_name = field_name[:-2]  # Remove 'Id' suffix
            if fk_validations or (view_spec and fk_name in view_spec):
            
                fk_data = {"exists": False}
                try:
                    fk_entity_cls = ModelImportCache.get_model_class(fk_name.capitalize())
                    related_entity_object: Dict[str, Any] = await fk_entity_cls.get(entity_dict[field_name])
                    related_data = related_entity_object.get('data', {})
                    # related_data = related_entity.model_dump()
                
                    fk_data = {"exists": True}
                    if view_spec and fk_name in view_spec:
                        requested_fields = view_spec[fk_name]
                    
                        # Handle case-insensitive field matching for URL parameter issues
                        field_map = {k.lower(): k for k in related_data.keys()}
                        
                        for field in requested_fields or []:
                            # Try exact match first, then case-insensitive fallback
                            if field in related_data:
                                fk_data[field] = related_data[field]
                            elif field.lower() in field_map:
                                actual_field = field_map[field.lower()]
                                fk_data[actual_field] = related_data[actual_field]
                        
                    
                except ImportError:
                    # FK entity class doesn't exist - skip validation
                    message = f"{fk_name} entity type does not exist"

                except NotFoundError:
                    # FK doesn't exist - always just set exists=False regardless of view
                    message = f"{fk_name}.id {entity_dict[field_name]} does not exist"

                except Exception as e:
                    message = f"Error processing {fk_name} for {entity_name} {entity_id}: {str(e)}"
                
                entity_dict[fk_name] = fk_data

                # Add FK validation warning only when view provided or GV enabled
                # (Model validation is handled separately and always runs)
                if fk_data.get('exists') is False:
                    notify_warning(
                        message=message,
                        type=NotificationType.VALIDATION,
                        entity=entity_name,
                        field_name=field_name,
                        value=entity_dict[field_name],
                        operation="get_data",
                        entity_id=entity_id
                    )


# Obsolete functions removed - FK processing now handled directly in models


def validate_with_notifications(cls, data: Dict[str, Any], entity_name: str, operation: str = "get_data"):
    """
    Validate data with Pydantic and convert errors to notifications.
    Returns the validated instance or unvalidated instance if validation fails.
    
    This handles basic model validation:
    - Enum validation (gender must be 'male', 'female', 'other')
    - Range validation (netWorth >= 0) 
    - String validation (length, format, etc.)
    - Type validation (int, float, bool, etc.)
    
    This does NOT handle FK validation - that's separate.
    """
    try:
        return cls.model_validate(data)
    except PydanticValidationError as e:
        entity_id = data.get('id', 'unknown')
        for error in e.errors():
            field_name = str(error['loc'][-1]) if error.get('loc') else 'unknown'
            notify_warning(
                message=error.get('msg', 'Validation error'),
                type=NotificationType.VALIDATION,
                entity=entity_name,
                field_name=field_name,
                value=error.get('input'),
                operation=operation,
                entity_id=entity_id
            )
        # Return unvalidated instance so API can continue
        return cls.model_construct(**data)


# get_entity_with_fk function removed - models now handle FK processing directly
