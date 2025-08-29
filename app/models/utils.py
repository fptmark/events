from typing import List, Dict, Any, Optional
from pydantic import ValidationError as PydanticValidationError
import warnings as python_warnings
from app.config import Config
from app.services.notification import validation_warning, system_error
from app.services.metadata import MetadataService

def process_raw_results(cls, entity_type: str, raw_docs: List[Dict[str, Any]], warnings: List[str]) -> List[Dict[str, Any]]:
    """Common processing for raw database results."""
    validations = Config.validation(True)
    entities = []

    # ALWAYS validate model data against Pydantic schema (enum, range, string validation, etc.)
    # This is independent of GV settings which only control FK validation
    for doc in raw_docs:
        entities.append(validate_model(cls, doc, entity_type))  

    # Database warnings are already processed by DatabaseFactory - don't duplicate

    # Convert models to dictionaries for FastAPI response validation
    entity_data = []
    for entity in entities:
        with python_warnings.catch_warnings(record=True) as caught_warnings:
            python_warnings.simplefilter("always")
            data_dict = entity.model_dump(mode='python')
            entity_data.append(data_dict)
            
            # Add any serialization warnings as notifications
            if caught_warnings:
                entity_id = data_dict.get('id')
                if not entity_id:
                    system_error("Document missing ID field")
                    entity_id = "missing"

                # Extract field names from warning messages  
                warning_field_names = set()
                for warning in caught_warnings:
                    warning_msg = str(warning.message)
                    
                    # Look for various Pydantic warning patterns
                    # Pattern 1: "Field 'fieldname' has invalid value" 
                    if "field" in warning_msg.lower() and "'" in warning_msg:
                        parts = warning_msg.split("'")
                        if len(parts) >= 2:
                            potential_field = parts[1]
                            if cls._metadata and potential_field in cls._metadata.get('fields', {}):
                                warning_field_names.add(potential_field)
                    
                    # Pattern 2: Check if warning is related to datetime fields based on message content
                    elif any(keyword in warning_msg.lower() for keyword in ['datetime', 'date', 'time', 'iso']):
                        # For datetime-related warnings, check all datetime fields in the data
                        for field_name, field_meta in cls._metadata.get('fields', {}).items():
                            if field_meta.get('type') in ['Date', 'Datetime', 'ISODate'] and field_name in data_dict:
                                warning_field_names.add(field_name)
                
                if warning_field_names:
                    field_list = ', '.join(sorted(warning_field_names))
                    validation_warning(f"Serialization warnings for fields: {field_list}", entity=entity_type, entity_id=entity_id)
                else:
                    # Fallback for warnings without extractable field names
                    warning_count = len(caught_warnings)
                    validation_warning(f"{entity_type} {entity_id}: {warning_count} serialization warnings", entity=entity_type, entity_id=entity_id)

    return entity_data


async def validate_fks(entity_name: str, data: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    """
    Worker function: Generic ObjectId reference validation for any entity.
    
    Args:
        entity_name: Name of the entity being validated (e.g., "User")
        data: Entity data dictionary to validate
        metadata: Entity metadata containing field definitions
    
    Raises:
        ValidationError: If any ObjectId references don't exist
    """
    from app.services.notification import validation_warning
    from app.routers.router_factory import ModelImportCache
    entity_id = data.get('id', 'unknown')
    
    # Check all ObjectId fields in the entity metadata
    for field_name, field_meta in metadata.get('fields', {}).items():
        if field_meta.get('type') == 'ObjectId' and data.get(field_name):
            fk_entity_name = MetadataService.get_proper_name(field_name[:-2])
            subobj = {'exists': False}
            try:
                # Derive FK entity name from field name (e.g., accountId -> Account)
                fk_entity_cls = ModelImportCache.get_model_class(fk_entity_name)
                response = await fk_entity_cls.get(data[field_name], None)
                
                # Check if FK exists - if not, send validation warning
                if not response.get('data'):
                    validation_warning(
                        message="Referenced ID does not exist",
                        entity=entity_name,
                        entity_id=entity_id,
                        field=field_name
                    )
                else:
                    subobj = {'exists': True}
            except Exception:
                # Handle import errors or other failures
                validation_warning(
                    message="internal error - model lookup failed during FK validation",
                    entity=entity_name,
                    entity_id=entity_id,
                    field=field_name
                )
            data[field_name[:-2]] = subobj  # Add FK field without 'Id' suffix
    
    # Note: FK validation failures are now handled through notification system




async def validate_uniques(entity_type: str, data: Dict[str, Any], unique_constraints: List[List[str]], exclude_id: Optional[str] = None) -> None:
    """
    Worker function: Validate unique constraints using database-specific implementation.
    Always enforced regardless of validation settings - unique constraints are business rules.
    
    Args:
        entity_type: Entity type to validate
        data: Entity data dictionary
        unique_constraints: List of unique constraint field groups
        exclude_id: ID to exclude from validation (for updates)
    
    Raises:
        ValidationError: If any unique constraints are violated
    """
    from app.db.factory import DatabaseFactory
    
    db = DatabaseFactory.get_instance()
    constraint_success = await db.documents._validate_unique_constraints(
        entity_type=entity_type,
        data=data,
        unique_constraints=unique_constraints,
        exclude_id=exclude_id
    )
    
    # For MongoDB, this will always be True (relies on native database constraints)
    # For Elasticsearch, this returns False if synthetic validation finds duplicates
    if not constraint_success:
        from app.services.notification import system_error
        system_error(f"Unique constraint violation for {entity_type}")
        # Note: MongoDB will throw DuplicateKeyError, Elasticsearch handles in _validate_unique_constraints


async def populate_view(entity_dict: Dict[str, Any], view_spec: Optional[Dict[str, Any]], entity_name: str) -> None:
    """
    Worker function: Populate FK view data in entity dictionary.
    
    Args:
        entity_dict: Entity data dictionary to populate
        view_spec: Dict of FK fields to populate with requested fields
        entity_name: Name of the entity type
    """
    if not view_spec:
        return
        
    from app.routers.router_factory import ModelImportCache
    
    metadata = MetadataService.get(entity_name)
    entity_id = entity_dict.get('id', 'unknown')
    
    for field_name, field_meta in metadata.get('fields', {}).items():
        if field_meta.get('type') == 'ObjectId' and entity_dict.get(field_name):
            fk_name = field_name[:-2]  # Remove 'Id' suffix
            if view_spec and fk_name in view_spec:
                fk_data = {"exists": False}
                try:
                    fk_entity_cls = ModelImportCache.get_model_class(MetadataService.get_proper_name(fk_name))
                    related_entity_object: Dict[str, Any] = await fk_entity_cls.get(entity_dict[field_name], None)
                    related_data = related_entity_object.get('data', {})
                
                    fk_data = {"exists": True}
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
                
                except Exception as e:
                    # FK lookup failed - set exists=False and continue
                    validation_warning(
                        message=f"Failed to populate {fk_name}: {str(e)}",
                        entity=entity_name,
                        entity_id=entity_id,
                        field=field_name
                    )
                
                entity_dict[fk_name] = fk_data


def validate_model(cls, data: Dict[str, Any], entity_name: str):
    """
    Worker function: Validate data with Pydantic and convert errors to notifications.
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
            validation_warning(
                message=error.get('msg', 'Validation error'),
                entity=entity_name,
                entity_id=entity_id,
                field=field_name
            )
        # Return unvalidated instance so API can continue
        return cls.model_construct(**data)




# get_entity_with_fk function removed - models now handle FK processing directly
