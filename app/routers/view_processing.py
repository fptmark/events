"""
View parameter processing for API endpoints.

Handles FK relationship population and validation based on 
view specifications from query parameters.

This module processes the 'view' parameter which allows clients to specify
which foreign key relationships should be included in the response, and which
specific fields from those relationships should be returned.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Type, TYPE_CHECKING
from urllib.parse import unquote

from app.config import Config
from app.routers.router_factory import ModelImportCache
from app.notification import notify_warning, NotificationType
from app.errors import NotFoundError

if TYPE_CHECKING:
    from typing import Protocol
    
    class EntityModelProtocol(Protocol):
        _metadata: Dict[str, Any]

logger = logging.getLogger(__name__)


async def process_view_data(response: Dict[str, Any], view_spec: Optional[Dict], 
                           entity_name: str, entity_cls: Type['EntityModelProtocol'], 
                           get_validations: bool) -> Dict[str, Any]:
    """
    Common view processing logic for both get_all and get_list endpoints.
    
    Processes FK includes if view parameter is provided, or auto-validates
    FK fields when get_validations=True and no view parameter provided.
    
    Args:
        response: The response dict containing 'data' key with entities
        view_spec: Parsed view parameter specifying FK fields to include
        entity_name: Name of the entity (e.g., "User")
        entity_cls: The entity model class
        get_validations: Whether FK validation is enabled
        
    Returns:
        Modified response dict with processed entity data
    """
    if not response.get('data'):
        return response
        
    # Process FK includes if view parameter is provided
    if view_spec:
        entity_data = []
        for entity in response.get('data', []):
            entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity
            await add_view_data(entity_dict, view_spec, entity_name, get_validations)
            entity_data.append(entity_dict)
        response['data'] = entity_data
    
    # Auto-validate FK fields when get_validations=True and no view parameter provided
    elif get_validations:
        entity_data = []
        for entity in response.get('data', []):
            entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity
            await auto_validate_fk_fields(entity_dict, entity_name, entity_cls)
            entity_data.append(entity_dict)
        response['data'] = entity_data
    
    return response


async def add_view_data(entity_dict: Dict[str, Any], view_spec: Optional[Dict[str, Any]], entity_name: str, get_validations: bool = False) -> None:
    """Add foreign key data to entity based on view specification."""
    if not view_spec:
        return
        
    try:
        # Process each FK in the view specification
        for fk_name, requested_fields in view_spec.items():
            fk_id_field = f"{fk_name}Id"
            
            # Check if entity has this FK field
            if fk_id_field in entity_dict and entity_dict[fk_id_field]:
                try:
                    # Import the related entity class
                    fk_entity_name = fk_name.capitalize()
                    fk_entity_cls = ModelImportCache.get_model_class(fk_entity_name)
                    
                    # Get the related entity
                    related_entity, _ = await fk_entity_cls.get(entity_dict[fk_id_field])
                    related_data = related_entity.model_dump()
                    
                    # Extract only the requested fields and add exists flag
                    fk_data = {"exists": True}
                    
                    # Handle case-insensitive field matching for URL parameter issues
                    # Some browsers (Chrome/Mac) convert URL params to lowercase
                    field_map = {k.lower(): k for k in related_data.keys()}
                    
                    for field in requested_fields or []:
                        # Try exact match first, then case-insensitive fallback
                        if field in related_data:
                            fk_data[field] = related_data[field]
                        elif field.lower() in field_map:
                            # Use the actual field name from the model
                            actual_field = field_map[field.lower()]
                            fk_data[actual_field] = related_data[actual_field]
                    
                    # Add the FK data to the entity
                    entity_dict[fk_name] = fk_data
                    
                except Exception as fk_error:
                    # Always display FK errors when view parameter provided - we're already doing the lookup
                    # Log FK lookup error but don't fail the whole request
                    entity_id = entity_dict.get('id', 'unknown')
                    
                    # Extract clean error message and format consistently
                    error_msg = str(fk_error)
                    fk_entity_name = fk_id_field[:-2].capitalize()  # Remove 'Id' suffix and capitalize
                    
                    # Router packages complete notification with all context
                    if "Document not found:" in error_msg:
                        # Extract the missing ID from the error
                        missing_id = error_msg.split("Document not found: ")[-1].strip()
                        missing_value = missing_id
                    elif "not found" in error_msg and "with ID" in error_msg:
                        # Extract ID from "account with ID 507f1f77bcf86cd799439011 was not found"
                        match = re.search(r'with ID (\w+)', error_msg)
                        if match:
                            missing_value = match.group(1)
                        else:
                            missing_value = entity_dict.get(fk_name, {}).get('id', 'unknown')
                    else:
                        missing_value = entity_dict.get(fk_id_field, 'unknown')
                    
                    # Add warning notification instead of raising ValidationError
                    # This allows data to be returned with FK validation warnings
                    notify_warning(
                        message=f"Id {missing_value} does not exist",
                        type=NotificationType.VALIDATION,
                        entity=entity_name,
                        field_name=fk_id_field,
                        value=missing_value,
                        operation="get_data",
                        entity_id=entity_id
                    )
                    
                    # Set FK data to indicate non-existence but continue processing
                    entity_dict[fk_name] = {"exists": False}
    
    except Exception as view_error:
        # Log view parsing error but continue without FK data
        notify_warning(f"Failed to parse view parameter: {str(view_error)}", NotificationType.VALIDATION, entity=entity_name)


async def auto_validate_fk_fields(entity_dict: Dict[str, Any], entity_name: str, entity_cls: Type['EntityModelProtocol']) -> None:
    """Auto-validate FK fields when get_validations enabled but no view parameter"""
    metadata = entity_cls._metadata
    entity_id = entity_dict.get('id', 'unknown')
    
    for field_name, field_meta in metadata.get('fields', {}).items():
        if field_meta.get('type') == 'ObjectId' and entity_dict.get(field_name):
            try:
                fk_entity_name = field_name[:-2].capitalize()  # Remove 'Id' suffix
                fk_entity_cls = ModelImportCache.get_model_class(fk_entity_name)
                await fk_entity_cls.get(entity_dict[field_name])
            except NotFoundError:
                # Add warning notification instead of raising ValidationError
                # This allows data to be returned with FK validation warnings
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


# Future optimization functions will be added here:
# 
# async def process_view_data_batch(response: Dict[str, Any], view_spec: Optional[Dict], 
#                                  entity_name: str, entity_cls: Type['EntityModelProtocol'], 
#                                  get_validations: bool) -> Dict[str, Any]:
#     """Batch-optimized version of process_view_data to eliminate N+1 queries."""
#     pass
#
# async def get_fk_data_batch(fk_ids_by_type: Dict[str, set]) -> Dict[str, Dict[str, Any]]:
#     """Batch fetch FK data by type to minimize database queries."""
#     pass