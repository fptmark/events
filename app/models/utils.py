from typing import List, Dict, Any, Optional
from pydantic import ValidationError as PydanticValidationError
import warnings as python_warnings
from app.config import Config
from app.services.notify import Notification, Warning, Error
from app.services.metadata import MetadataService
from app.services.model import ModelService

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
                    Notification.error(Error.SYSTEM, "Document missing ID field")
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
                    Notification.warning(Warning.DATA_VALIDATION, "Serialization warnings for fields", entity_type=entity_type, entity_id=entity_id, value=field_list)
                else:
                    # Fallback for warnings without extractable field names
                    warning_count = len(caught_warnings)
                    Notification.warning(Warning.DATA_VALIDATION, "Serialization warnings", entity_type=entity_type, entity_id=entity_id, value=str(warning_count))

    return entity_data


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
        Notification.error(Error.SYSTEM, f"Unique constraint violation for {entity_type}")
        # Note: MongoDB will throw DuplicateKeyError, Elasticsearch handles in _validate_unique_constraints


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
            Notification.warning(Warning.DATA_VALIDATION, "Validation error", entity_type=entity_name, entity_id=entity_id, field=field_name, value=error.get('msg', 'Validation error'))
        # Return unvalidated instance so API can continue
        return cls.model_construct(**data)


async def process_fks(entity_type: str, data: Dict[str, Any], validate: bool, view_spec: Dict[str, Any] = {}) -> None:
    """
    Unified FK processing: validation + view population in single pass.
    Only makes DB calls when data is actually needed.
    """
    
    fk_data = None
    for field_name, field_meta in MetadataService.fields(entity_type).items():
        # process every FK field if validating OR if it's in the view spec
        if field_meta.get('type') == 'ObjectId' and len(field_name) > 2:
            fk_name = field_name[:-2]  # Remove 'Id' suffix to get FK entity name

            if validate or fk_name.lower() in view_spec.keys():
                fk_entity_type = MetadataService.get_proper_name(fk_name)
                fk_data = {"exists": False}
                fk_field_id = data.get(field_name, None)
                
                if fk_field_id:
                    fk_cls = ModelService.get_model_class(fk_entity_type)
                    
                    if fk_cls:
                        # Fetch FK record
                        with Notification.suppress_warnings():  # suppress warnings when fetching a fk as the code below has a better warning (it includes the offending field)
                            related_data, count = await fk_cls.get(fk_field_id, None)
                        
                        # if there is more than one fk record, something is very wrong
                        if count == 1:
                            fk_data["exists"] = True
                            
                            # Populate requested fields if view_spec provided
                            if fk_entity_type.lower() in view_spec.keys():
                                # Handle case-insensitive field matching
                                field_map = {k.lower(): k for k in related_data.keys()}
                                
                                for field in view_spec[fk_entity_type.lower()] or []:
                                    if field in related_data:
                                        fk_data[field] = related_data[field]
                                    elif field.lower() in field_map:
                                        actual_field = field_map[field.lower()]
                                        fk_data[actual_field] = related_data[actual_field]
                                    else: # viewspec field not found in related entity
                                        Notification.warning(Warning.BAD_NAME, "Field not found in related entity", entity_type=entity_type, entity_id=data['id'], field=field)
                                        
                        elif count == 0:
                            # FK record not found - validation warning if validating
                            Notification.warning(Warning.NOT_FOUND, "Referenced ID does not exist", entity_type=entity_type, entity_id=data['id'], field=field_name, value=fk_field_id)
                        else:
                            # Multiple records - data integrity issue
                            Notification.warning(Warning.DATA_VALIDATION, "Multiple FK records found. Data integrity issue?", entity_type=entity_type, entity_id=data['id'], field=field_name, value=fk_field_id)
                            
                    else:
                        Notification.warning(Warning.NOT_FOUND, "FK entity does not exist", entity_type=entity_type, entity_id=data['id'], field=field_name, value=fk_entity_type)
                else:
                    # Invalid entity class or missing ID - validation warning if validating and required or entity in view spec
                    if (validate and field_meta.get('required', False)) or fk_name.lower() in view_spec.keys():
                        Notification.warning(Warning.MISSING, "Missing fk ID", entity_type=entity_type, entity_id=data['id'], field=field_name)
                
                # Set FK field data (inside the loop for each FK)
                if fk_data:
                    data[fk_name] = fk_data  


    def _get_proper_view_fields(self, view_spec: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Get view spec with proper case field names if database is case-sensitive"""
        if not view_spec or not self.isInternallyCaseSensitive():
            return view_spec

        proper_view_spec = {}
        for fk_entity_name, field_list in view_spec.items():
            # Convert the foreign entity name to proper case
            proper_fk_entity_name = MetadataService.get_proper_name(fk_entity_name)

            # Convert each field name in the field list to proper case
            proper_field_list = []
            for field_name in field_list:
                proper_field_name = MetadataService.get_proper_name(fk_entity_name, field_name)
                proper_field_list.append(proper_field_name)

            proper_view_spec[proper_fk_entity_name] = proper_field_list

        return proper_view_spec