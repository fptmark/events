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
        try:
            entities.append(cls.model_validate(doc))
        except PydanticValidationError as e:
            # Convert Pydantic errors to notifications
            entity_id = doc.get('id')
            if not entity_id:
                notify_warning("Document missing ID field", NotificationType.DATABASE, entity=entity_type)
                entity_id = "missing"

            for error in e.errors():
                field_name = str(error['loc'][-1])
                notify_warning(
                    message=error['msg'],
                    type=NotificationType.VALIDATION,
                    entity=entity_type,
                    field_name=field_name,
                    value=error.get('input'),
                    operation="get_data",
                    entity_id=entity_id
                )

            # Create instance without validation for failed docs
            entities.append(cls.model_construct(**doc))  

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


def should_process_fk_fields(operation_is_get_all: bool, has_view_spec: bool) -> bool:
    """
    Determine if FK fields should be processed based on user's original rules:
    
    1. View parameter ALWAYS triggers FK processing regardless of get_validations
    2. get_validations="get" applies only to single get operations  
    3. get_validations="get_all" applies to all read operations
    
    Args:
        operation_is_get_all: True for get_all/list, False for single get
        has_view_spec: Whether view parameter was provided
        
    Returns:
        True if FK fields should be processed
    """
    # Rule 1: View parameter always triggers FK processing
    if has_view_spec:
        return True
        
    # Rules 2 & 3: Check get_validations setting
    get_validation, _ = Config.validations(operation_is_get_all)
    return get_validation




async def process_entity_fks(entity_dict: Dict[str, Any], view_spec: Optional[Dict[str, Any]], 
                           entity_name: str, entity_cls) -> None:
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
            
            try:
                fk_entity_cls = ModelImportCache.get_model_class(fk_name.capitalize())
                related_entity, _ = await fk_entity_cls.get(entity_dict[field_name])
                related_data = related_entity.model_dump()
                
                if view_spec and fk_name in view_spec:
                    # View case: populate requested fields
                    requested_fields = view_spec[fk_name]
                    fk_data = {"exists": True}
                    
                    # Handle case-insensitive field matching for URL parameter issues
                    field_map = {k.lower(): k for k in related_data.keys()}
                    
                    for field in requested_fields or []:
                        # Try exact match first, then case-insensitive fallback
                        if field in related_data:
                            fk_data[field] = related_data[field]
                        elif field.lower() in field_map:
                            actual_field = field_map[field.lower()]
                            fk_data[actual_field] = related_data[actual_field]
                    
                    entity_dict[fk_name] = fk_data
                else:
                    # GV case: just set exists flag
                    entity_dict[fk_name] = {"exists": True}
                    
            except NotFoundError:
                # FK doesn't exist - always just set exists=False regardless of view
                entity_dict[fk_name] = {"exists": False}
                
                # Add FK validation warning only when view provided or GV enabled
                # (Model validation is handled separately and always runs)
                get_validations, _ = Config.validations(False)
                if view_spec or get_validations:
                    notify_warning(
                        message=f"Id {entity_dict[field_name]} does not exist",
                        type=NotificationType.VALIDATION,
                        entity=entity_name,
                        field_name=field_name,
                        value=entity_dict[field_name],
                        operation="get_data",
                        entity_id=entity_id
                    )
            except ImportError:
                # FK entity class doesn't exist - skip validation
                pass


async def process_response_data(response: Dict[str, Any], view_spec: Dict[str, Any], 
                               entity_name: str, entity_cls, operation_is_get_all: bool) -> Dict[str, Any]:
    """
    Process response data with FK fields in the model layer.

    This consolidates ALL FK processing logic into the model layer,
    removing it from routers to fix Separation of Concerns.

    FK Processing Rules:
    1. View parameter provided → Process view specs (includes FK validation)
    2. No view + GV enabled → Auto-validate all FK fields 
    3. No view + GV disabled → No FK processing

    Args:
        response: Response dict with 'data' key
        view_spec: Parsed view parameter (None if not provided)
        entity_name: Name of the entity type
        entity_cls: Entity model class
        operation_is_get_all: True for get_all/list operations
        
    Returns:
        Modified response with processed FK data (always returns data)
    """
    if not response.get('data'):
        return response
    
    # Process entities (handle both single entity and list)
    data = response['data']
    if isinstance(data, list):
        # Multiple entities
        processed_data = []
        for entity in data:
            entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity
            await _process_single_entity_fks(entity_dict, view_spec, entity_name, entity_cls, operation_is_get_all)
            processed_data.append(entity_dict)
        response['data'] = processed_data
    else:
        # Single entity
        entity_dict = data.model_dump() if hasattr(data, 'model_dump') else data
        await _process_single_entity_fks(entity_dict, view_spec, entity_name, entity_cls, operation_is_get_all)
        response['data'] = entity_dict
    
    return response


async def _process_single_entity_fks(entity_dict: Dict[str, Any], view_spec: Dict[str, Any], 
                                    entity_name: str, entity_cls, operation_is_get_all: bool) -> None:
    """
    Process FK fields for a single entity - simplified to use unified function.
    """
    # Determine if FK processing should happen
    if view_spec or should_process_fk_fields(operation_is_get_all, view_spec is not None):
        await process_entity_fks(entity_dict, view_spec, entity_name, entity_cls)


async def validate_entity_model(entity_dict: Dict[str, Any], entity_name: str, entity_cls) -> None:
    """
    Always validate entity against its Pydantic model - independent of FK processing.
    
    This handles basic model validation:
    - Enum validation (gender must be 'male', 'female', 'other')
    - Range validation (netWorth >= 0)
    - String validation (length, format, etc.)
    - Type validation (int, float, bool, etc.)
    
    This does NOT handle FK validation - that's separate.
    """
    entity_id = entity_dict.get('id', 'unknown')
    
    try:
        # Validate the entity data against its Pydantic model
        entity_cls.model_validate(entity_dict)
        # If validation passes, no notifications needed
    except PydanticValidationError as e:
        # Convert Pydantic validation errors to notifications
        for error in e.errors():
            field_name = str(error['loc'][-1]) if error.get('loc') else 'unknown'
            message = error.get('msg', 'Validation error')
            value = error.get('input')
            
            notify_warning(
                message=message,
                type=NotificationType.VALIDATION,
                entity=entity_name,
                field_name=field_name,
                value=value,
                operation="get_data",
                entity_id=entity_id
            )


async def get_entity_with_fk(entity_cls, entity_id: str, view_spec: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get single entity with FK processing - works for any entity type."""
    entity, warnings = await entity_cls.get(entity_id)
    entity_dict = entity.model_dump()
    entity_name = entity_cls.__name__
    
    # Step 1: ALWAYS run model validation (enum, range, string validation, etc.)
    await validate_entity_model(entity_dict, entity_name, entity_cls)
    
    # Step 2: Conditionally run FK processing based on GV settings or view parameter
    get_validations, _ = Config.validations(False)
    if view_spec or get_validations:
        await process_entity_fks(entity_dict, view_spec, entity_name, entity_cls)
    
    return {"data": entity_dict, "warnings": warnings}
