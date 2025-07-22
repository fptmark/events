"""
Reusable CRUD endpoint handlers for dynamic router creation.

This module contains the core CRUD endpoint logic that can be reused
across different entity routers, including FK data processing and
notification handling.
"""

import json
import logging
from typing import Dict, Any, Type
from urllib.parse import unquote
from fastapi import Request

from app.config import Config
from app.routers.router_factory import ModelImportCache
from app.notification import (
    start_notifications, end_notifications,
    notify_success, notify_error, notify_warning, notify_validation_error,
    NotificationType
)
from app.errors import ValidationError, NotFoundError, DuplicateError

logger = logging.getLogger(__name__)


async def auto_validate_fk_fields(entity_dict: Dict[str, Any], entity_name: str, entity_cls: Type) -> None:
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
                # Router packages complete notification with all context - same format as model validation
                fk_entity_name = field_name[:-2].capitalize()  # Remove 'Id' suffix and capitalize
                notify_warning(f"{fk_entity_name} {entity_dict[field_name]} not found", 
                             NotificationType.DATABASE, 
                             entity=entity_name, 
                             entity_id=entity_id, 
                             field_name=field_name, 
                             value=entity_dict[field_name])
            except ImportError:
                # FK entity class doesn't exist - skip validation
                pass


async def add_view_data(entity_dict: Dict[str, Any], view_spec: Dict[str, Any] | None, entity_name: str, get_validations: bool = False) -> None:
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
                    
                    for field in requested_fields:
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
                        import re
                        match = re.search(r'with ID (\w+)', error_msg)
                        if match:
                            missing_value = match.group(1)
                        else:
                            missing_value = entity_dict.get(fk_name, {}).get('id', 'unknown')
                    else:
                        missing_value = entity_dict.get(fk_name, {}).get('id', 'unknown')
                    
                    notify_warning(f"{fk_entity_name} {missing_value} not found", 
                                 NotificationType.DATABASE, 
                                 entity=entity_name, 
                                 entity_id=entity_id, 
                                 field_name=fk_id_field, 
                                 value=missing_value)
                    # Return an object indicating the FK doesn't exist
                    entity_dict[fk_name] = {"exists": False}
    
    except Exception as view_error:
        # Log view parsing error but continue without FK data
        notify_warning(f"Failed to parse view parameter: {str(view_error)}", NotificationType.VALIDATION, entity=entity_name)


async def list_entities_handler(entity_cls: Type, entity_name: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for LIST endpoint."""
    get_validations, _ = Config.validations(True)
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"list_{entity_lower}s")
    
    # Extract query parameters for FK processing
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    try:
        # Get data from model (model will add notifications to current context)
        response = await entity_cls.get_all()
        
        # Process FK includes if view parameter is provided and we have data
        if response.get('data') and view_spec:
            entity_data = []
            for entity in response['data']:
                entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity
                await add_view_data(entity_dict, view_spec, entity_name, get_validations)
                entity_data.append(entity_dict)
            response['data'] = entity_data
        
        # Auto-validate FK fields when get_validations=True and no view parameter provided
        elif response.get('data') and get_validations and not view_spec:
            entity_data = []
            for entity in response['data']:
                entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity
                await auto_validate_fk_fields(entity_dict, entity_name, entity_cls)
                entity_data.append(entity_dict)
            response['data'] = entity_data
        
        collection = end_notifications()
        return collection.to_entity_grouped_response(data=response['data'], is_bulk=True)
    except Exception as e:
        notify_error(f"Failed to retrieve entities: {str(e)}", NotificationType.SYSTEM, entity=entity_name)
        collection = end_notifications()
        return collection.to_entity_grouped_response(data=[], is_bulk=True)
    finally:
        end_notifications()


async def get_entity_handler(entity_cls: Type, entity_name: str, entity_id: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for GET endpoint."""
    get_validations, _ = Config.validations(False)
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"get_{entity_lower}")
    
    # Extract query parameters for FK processing
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    try:
        entity, warnings = await entity_cls.get(entity_id)
        
        # Add any warnings as notifications
        for warning in warnings:
            notify_warning(warning, NotificationType.DATABASE)
        
        # Process FK includes if view parameter is provided
        # Serialize entity data (datetime warnings should be eliminated by json_encoders)
        entity_dict = entity.model_dump()
        
        # entity_dict['exists'] = True  # If no exception thrown, entity exists
        await add_view_data(entity_dict, view_spec, entity_name, get_validations)
        
        # Auto-validate FK fields when get_validations=True and no view parameter provided
        if get_validations and not view_spec:
            await auto_validate_fk_fields(entity_dict, entity_name, entity_cls)
        
        collection = end_notifications()
        return collection.to_entity_grouped_response(entity_dict, is_bulk=False)
    except NotFoundError:
        # Let the NotFoundError bubble up to FastAPI's exception handler
        # which will return a proper 404 response
        end_notifications()
        raise
    except Exception as e:
        notify_error(f"Failed to retrieve entity: {str(e)}", NotificationType.SYSTEM, entity=entity_name)
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    finally:
        end_notifications()


async def create_entity_handler(entity_cls: Type, entity_name: str, entity_data: Any) -> Dict[str, Any]:
    """Reusable handler for POST endpoint."""
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"create_{entity_lower}")
    
    try:
        # Let model handle all validation and business logic
        entity = entity_cls(**entity_data.model_dump())
        result, warnings = await entity.save()
        # Add any warnings from save operation
        for warning in warnings:
            notify_warning(warning, NotificationType.DATABASE)
        notify_success("Created successfully", NotificationType.BUSINESS, entity=entity_name)
        collection = end_notifications()
        return collection.to_entity_grouped_response(result.model_dump(), is_bulk=False)
    except (ValidationError, DuplicateError):
        # Let these exceptions bubble up to FastAPI exception handlers
        # which will return proper HTTP status codes (422, 409)
        end_notifications()
        raise
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        end_notifications()
        raise
    finally:
        end_notifications()


async def update_entity_handler(entity_cls: Type, entity_name: str, entity_id: str, entity_data: Any) -> Dict[str, Any]:
    """Reusable handler for PUT endpoint - True PUT semantics (full replacement)."""
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"update_{entity_lower}")
    
    try:
        # True PUT semantics: validate complete entity data with URL's entity_id
        entity_dict = entity_data.model_dump()
        validated_entity = entity_cls.model_validate(entity_dict)
        
        # Save with entity_id from URL (authoritative) - this handles auto-fields internally
        result, save_warnings = await validated_entity.save(entity_id=entity_id)
        
        # Add any warnings from save operation
        for warning in save_warnings:
            notify_warning(warning, NotificationType.DATABASE)
        notify_success("Updated successfully", NotificationType.BUSINESS, entity=entity_name)
        collection = end_notifications()
        return collection.to_entity_grouped_response(result.model_dump(), is_bulk=False)
    except (NotFoundError, ValidationError, DuplicateError):
        # Let these exceptions bubble up to FastAPI exception handlers
        # which will return proper HTTP status codes (404, 422, 409)
        end_notifications()
        raise
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        end_notifications()
        raise
    finally:
        end_notifications()


async def delete_entity_handler(entity_cls: Type, entity_name: str, entity_id: str) -> Dict[str, Any]:
    """Reusable handler for DELETE endpoint."""
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"delete_{entity_lower}")
    
    try:
        success, warnings = await entity_cls.delete(entity_id)
        if success:
            notify_success("Deleted successfully", NotificationType.BUSINESS, entity=entity_name)
        for warning in warnings:
            notify_warning(warning, NotificationType.DATABASE)
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    except NotFoundError:
        # Let NotFoundError bubble up to FastAPI exception handler
        # which will return proper HTTP status code (404)
        end_notifications()
        raise
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        end_notifications()
        raise
    finally:
        end_notifications()