from typing import List, Dict, Any
from pydantic import ValidationError as PydanticValidationError
import warnings as python_warnings
from app.config import Config
from app.notification import notify_warning, NotificationType

def process_raw_results(cls, entity_type: str, raw_docs: List[Dict[str, Any]], warnings: List[str]) -> List[Dict[str, Any]]:
    """Common processing for raw database results."""
    get_validations, _ = Config.validations(True)
    entities = []

    # Conditional validation - validate AFTER read if requested
    if get_validations:
        for doc in raw_docs:
            try:
                entities.append(cls.model_validate(doc))
            except PydanticValidationError as e:
                # Convert Pydantic errors to notifications (match original get_all logic)
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
    else:
        entities = [cls.model_construct(**doc) for doc in raw_docs]  # NO validation  

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
