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
from app.services.model import ModelService
from app.services.notification import validation_warning
from app.services.metadata import MetadataService

if TYPE_CHECKING:
    from app.routers.router_factory import EntityModelProtocol

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
            await add_view_data(entity_dict, view_spec, entity_name)
            entity_data.append(entity_dict)
        response['data'] = entity_data
    
    # Auto-validate FK fields when get_validations=True and no view parameter provided
    elif get_validations:
        entity_data = []
        for entity in response.get('data', []):
            entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity
            await _validate_fk_fields(entity_dict, entity_name, entity_cls)
            entity_data.append(entity_dict)
        response['data'] = entity_data
    
    return response


async def _process_fk_field(entity_dict: Dict[str, Any], fk_name: str, fk_id_field: str, 
                           requested_fields: Optional[list], entity_name: str) -> Dict[str, Any]:
    """Common FK processing logic for both view and validation operations."""
    fk_data = {"exists": False}
    
    # 1. Check if FK entity class exists
    fk_entity_cls = ModelService.get_model_class(fk_name)
    if fk_entity_cls:
        # 2. Check if entity has FK ID field
        if fk_id_field in entity_dict and entity_dict[fk_id_field]:
            # 3. Try to get the FK record
            related_response = await fk_entity_cls.get(entity_dict[fk_id_field], None)
            related_data = related_response.get('data', None)
            
            if related_data:
                # Success - FK record exists
                fk_data = {"exists": True}
                
                # Extract requested fields if specified (view processing)
                if requested_fields:
                    fk_field_map = {k.lower(): k for k in related_data.keys()}
                    
                    for view_field in requested_fields:
                        # 4. Check if requested field exists in FK record
                        if view_field in related_data:
                            fk_data[view_field] = related_data[view_field]
                        elif view_field.lower() in fk_field_map:
                            actual_field = fk_field_map[view_field.lower()]
                            fk_data[actual_field] = related_data[actual_field]
                        else:
                            # FK field not found in related entity
                            validation_warning(
                                message="Field not found in related entity",
                                entity=fk_name,
                                field=view_field
                            )
            else:
                # FK record missing (broken ref integrity)
                validation_warning(
                    message="FK record not found",
                    entity=fk_name,
                    entity_id=entity_dict[fk_id_field]
                )
        else:
            # FK ID field missing in entity
            validation_warning(
                message="Missing FK ID field",
                entity=entity_name,
                field=fk_id_field
            )
    else:
        # FK entity does not exist (bad entity name in view spec)
        validation_warning(
            message="Invalid entity in view specification",
            entity=fk_name
        )
    
    return fk_data


async def add_view_data(entity_dict: Dict[str, Any], view_spec: Dict[str, Any], entity_name: str) -> None:
    """Add foreign key data to entity based on view specification."""
    for fk_name, requested_fields in view_spec.items():
        fk_id_field = f"{fk_name}Id"
        fk_data = await _process_fk_field(entity_dict, fk_name, fk_id_field, requested_fields, entity_name)
        entity_dict[fk_name.lower()] = fk_data
            

async def _validate_fk_fields(entity_dict: Dict[str, Any], entity_name: str, entity_cls: Type['EntityModelProtocol']) -> None:
    """Auto-validate FK fields when get_validations enabled"""
    
    for field_name, field_meta in MetadataService.fields(entity_name).items():
        if field_meta.get('type') == 'ObjectId' and entity_dict.get(field_name):
            fk_entity_name = MetadataService.get_proper_name(field_name[:-2])  # Remove 'Id' suffix
            fk_data = await _process_fk_field(entity_dict, fk_entity_name, field_name, None, entity_name)
            entity_dict[fk_entity_name.lower()] = fk_data


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