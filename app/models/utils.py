from typing import List, Dict, Any, Optional
from pydantic import ValidationError as PydanticValidationError
import warnings as python_warnings
from app.config import Config
from app.services.notification import Notification, validation_warning, system_error
from app.services.metadata import MetadataService
from app.services.model import ModelService
from app.services.request_context import RequestContext

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


# async def validate_fks(entity_name: str, data: Dict[str, Any], metadata: Dict[str, Any]) -> None:
#     """
#     Worker function: Generic ObjectId reference validation for any entity.
    
#     Args:
#         entity_name: Name of the entity being validated (e.g., "User")
#         data: Entity data dictionary to validate
#         metadata: Entity metadata containing field definitions
    
#     Raises:
#         ValidationError: If any ObjectId references don't exist
#     """
#     from app.services.notification import validation_warning
#     from app.services.model import ModelService
    
#     # Check all ObjectId fields in the entity metadata
#     for field_name, field_meta in metadata.get('fields', {}).items():
#         if field_meta.get('type') == 'ObjectId' and data.get(field_name):
#             fk_entity_name = MetadataService.get_proper_name(field_name[:-2])
#             subobj = {'exists': False}
#             # Derive FK entity name from field name (e.g., accountId -> Account)
#             fk_entity_cls = ModelService.get_model_class(fk_entity_name)
#             if fk_entity_cls:
#                 response = await fk_entity_cls.get(data[field_name], None)
                
#                 # Check if FK exists
#                 if response.get('data'):
#                     subobj = {'exists': True}
#                 else:
#                     validation_warning(
#                         message="Referenced ID does not exist",
#                         entity=fk_entity_name,
#                         entity_id=data[field_name],
#                         field=field_name
#                     )
#             else:
#                 # Bad entity name in FK reference
#                 validation_warning(
#                     message=f"Invalid FK entity", 
#                     entity=fk_entity_name,
#                     field=field_name
#                 )
#             data[fk_entity_name.lower()] = subobj  # Add FK field without 'Id' suffix
    
#     # Note: FK validation failures are now handled through notification system




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


# async def populate_view(entity_dict: Dict[str, Any], view_spec: Optional[Dict[str, Any]], entity_name: str) -> None:
#     """
#     Worker function: Populate FK view data in entity dictionary.
    
#     Args:
#         entity_dict: Entity data dictionary to populate
#         view_spec: Dict of FK fields to populate with requested fields
#         entity_name: Name of the entity type
#     """
#     if not view_spec:
#         return
        
    
#     metadata = MetadataService.get(entity_name)
#     entity_id = entity_dict.get('id', 'unknown')
    
#     for field_name, field_meta in metadata.get('fields', {}).items():
#         if field_meta.get('type') == 'ObjectId' and entity_dict.get(field_name):
#             fk_name = field_name[:-2]  # Remove 'Id' suffix
#             if view_spec and fk_name in view_spec:
#                 fk_data = {"exists": False}
#                 fk_entity_cls = ModelService.get_model_class(MetadataService.get_proper_name(fk_name))
#                 if fk_entity_cls:
#                     try:
#                         related_data, count = await fk_entity_cls.get(entity_dict[field_name], None)
                    
#                         if count == 1:
#                             fk_data = {"exists": True}
#                             requested_fields = view_spec[fk_name]
                        
#                             # Handle case-insensitive field matching for URL parameter issues
#                             field_map = {k.lower(): k for k in related_data.keys()}
                            
#                             for field in requested_fields or []:
#                                 # Try exact match first, then case-insensitive fallback
#                                 if field in related_data:
#                                     fk_data[field] = related_data[field]
#                                 elif field.lower() in field_map:
#                                     actual_field = field_map[field.lower()]
#                                     fk_data[actual_field] = related_data[actual_field]
#                         elif count == 0:
#                             # FK record missing (broken ref integrity)
#                             validation_warning(
#                                 message="FK record not found",
#                                 entity=fk_name,
#                                 entity_id=entity_dict[field_name],
#                                 field=field_name
#                             )
#                         else:
#                             # Multiple FK records found - should not happen with ObjectId
#                             validation_warning(
#                                 message="Multiple FK records found.  Data integrity issue?",
#                                 entity=fk_name,
#                                 entity_id=entity_dict[field_name],
#                                 field=field_name
#                             )
                    
#                     except Exception as e:
#                         # FK lookup failed - set exists=False and continue
#                         validation_warning(
#                             message=f"Failed to populate {fk_name}: {str(e)}",
#                             entity=entity_name,
#                             entity_id=entity_id,
#                             field=field_name
#                         )
#                 else:
#                     # Bad entity name in view spec
#                     validation_warning(
#                         message=f"Invalid entity '{fk_name}' in view specification",
#                         entity=entity_name,
#                         entity_id=entity_id,
#                         field=field_name
#                     )
                
#                 entity_dict[fk_name] = fk_data


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

# def build_error_response(status: str) -> Dict[str, Any]:

#     """Build standardized error response when validation fails before DB operation."""
#     return {
#         "data": {},
#         "notifications": Notification.end().get("notifications", {}),
#         "status": status
#     }

# def build_standard_response(data: Any, total_records: int) -> Dict[str, Any]:
#     """
#     Build a standardized API response dictionary from internal response.
    
#     Args:
#         response: Internal response dictionary with keys like 'data', 'errors', 'warnings', 'notifications', 'total_records'
    
#     Returns:
#         Standardized response dictionary with keys: 'data', 'notifications', 'status', 'pagination'
#     """
#     result: Dict[str, Any] = {}

#     result["data"] = data

#     notification_response = Notification.end()
#     notifications = notification_response.get("notifications", {})
#     result["notifications"] = notifications

#     errors = notifications.get('errors', [])
#     warnings = notifications.get('warnings', {})
#     status = "success" if len(errors) == 0 and len(warnings) == 0 else "warning" if len(warnings) > 0 else "error"
#     result["status"] = status

#     if isinstance(data, List):
#         result["pagination"] = pagination(RequestContext.page, total_records, RequestContext.pageSize)

#     return result


# def pagination(page: int, totalRecords: int, pageSize: int = 25) -> Dict[str, Any]:
#     """
#     Build pagination response structure used by all models.
    
#     Args:
#         page: Current page number
#         pageSize: Items per page  
#         totalRecords: Total number of items
        
#     Returns:
#         Dictionary with pagination fields matching existing pattern
#     """
#     totalPages = (totalRecords + pageSize - 1) // pageSize if totalRecords > 0 else 0
    
#     return {
#         "page": page,
#         "pageSize": pageSize,
#         "total": totalRecords,
#         "totalPages": totalPages
#     }



# get_entity_with_fk function removed - models now handle FK processing directly


async def process_fks(entity_type: str, data: Dict[str, Any], validate: bool, view_spec: Dict[str, Any] = {}) -> None:
    """
    Unified FK processing: validation + view population in single pass.
    Only makes DB calls when data is actually needed.
    """
    
    for field_name, field_meta in MetadataService.fields(entity_type).items():
        # process every FK field if validating OR if it's in the view spec
        if field_meta.get('type') == 'ObjectId' and len(field_name) > 2:
            fk_name = field_name[:-2]  # Remove 'Id' suffix to get FK entity name
            fk_entity_type = MetadataService.get_proper_name(fk_name)
            fk_data = {"exists": False}

            if validate or fk_name.lower() in view_spec.keys():
                fk_field_id = data.get(field_name, None)
                
                if fk_field_id:
                    fk_cls = ModelService.get_model_class(fk_entity_type)
                    
                    if fk_cls:
                        # Fetch FK record
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
                                        validation_warning(
                                            message="Field not found in related entity",
                                            entity=entity_type,
                                            entity_id=data['id'],
                                            field=field
                                        )
                                        
                        elif count == 0:
                            # FK record not found - validation warning if validating
                            validation_warning(
                                message="Referenced ID does not exist",
                                entity=entity_type,
                                entity_id=data['id'],
                                field=field_name
                            )
                        else:
                            # Multiple records - data integrity issue
                            validation_warning(
                                message="Multiple FK records found. Data integrity issue?",
                                entity=entity_type,
                                entity_id=data['id'],
                                field=field_name
                            )
                            
                    else:
                        validation_warning(
                            message="FK entity does not exist",
                            entity=entity_type,
                            entity_id=data['id'],
                            field=field_name
                        )
                else:
                    # Invalid entity class or missing ID - validation warning if validating and required or entity in view spec
                    if (validate and field_meta.get('required', False)) or fk_name.lower() in view_spec.keys():
                        validation_warning(
                            message="Missing fk ID",
                            entity=entity_type,
                            entity_id=data['id'],
                            field=field_name
                        )
                
                # Set FK field data (inside the loop for each FK)
                data[fk_name] = fk_data  