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

from app.routers.router_factory import ModelImportCache
from app.notification import (
    start_notifications, end_notifications,
    notify_success, notify_error, notify_warning, notify_validation_error,
    NotificationType
)
from app.errors import ValidationError, NotFoundError, DuplicateError

logger = logging.getLogger(__name__)


async def add_view_data(entity_dict: Dict[str, Any], view_spec: Dict[str, Any] | None, entity_name: str) -> None:
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
                    # Log FK lookup error but don't fail the whole request
                    notify_warning(f"Failed to load {fk_name} for {entity_name}: {str(fk_error)}", NotificationType.DATABASE)
                    # Return an object indicating the FK doesn't exist
                    entity_dict[fk_name] = {"exists": False}
    
    except Exception as view_error:
        # Log view parsing error but continue without FK data
        notify_warning(f"Failed to parse view parameter: {str(view_error)}", NotificationType.VALIDATION)


async def list_entities_handler(entity_cls: Type, entity_name: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for LIST endpoint."""
    entity_lower = entity_name.lower()
    
    # Extract query parameters for FK processing
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    try:
        # Get entity-grouped response from model
        response = await entity_cls.get_all()
        
        # Process FK includes if view parameter is provided and we have data
        if response.get('data') and view_spec:
            entity_data = []
            for entity in response['data']:
                entity_dict = entity.model_dump() if hasattr(entity, 'model_dump') else entity
                await add_view_data(entity_dict, view_spec, entity_name)
                entity_data.append(entity_dict)
            response['data'] = entity_data
        
        return response
    except Exception as e:
        # For system failures, return failed response with no data
        from app.notification import start_notifications, end_notifications, NotificationLevel, NotificationType
        notifications = start_notifications(entity_name, f"list_{entity_lower}s")
        notifications.add(
            message=f"Failed to retrieve {entity_lower}s: {str(e)}",
            level=NotificationLevel.ERROR,
            type=NotificationType.SYSTEM
        )
        collection = end_notifications()
        return collection.to_entity_grouped_response(data=[], is_bulk=True)


async def get_entity_handler(entity_cls: Type, entity_name: str, entity_id: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for GET endpoint."""
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
        entity_dict = entity.model_dump()
        # entity_dict['exists'] = True  # If no exception thrown, entity exists
        await add_view_data(entity_dict, view_spec, entity_name)
        
        collection = end_notifications()
        return collection.to_entity_grouped_response(entity_dict, is_bulk=False)
    except NotFoundError:
        notify_error(f"{entity_name} not found", NotificationType.BUSINESS)
        # Return object with exists=False for consistent UI handling
        not_found_entity = {"id": entity_id} #, "exists": False}
        collection = end_notifications()
        return collection.to_entity_grouped_response(not_found_entity, is_bulk=False)
    except Exception as e:
        notify_error(f"Failed to retrieve {entity_lower}: {str(e)}", NotificationType.SYSTEM)
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
        notify_success(f"{entity_name} created successfully", NotificationType.BUSINESS)
        collection = end_notifications()
        return collection.to_entity_grouped_response(result.model_dump(), is_bulk=False)
    except (ValidationError, DuplicateError) as e:
        notify_validation_error(f"Failed to create {entity_lower}: {str(e)}")
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    except Exception as e:
        notify_error(f"Failed to create {entity_lower}: {str(e)}", NotificationType.SYSTEM)
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    finally:
        end_notifications()


async def update_entity_handler(entity_cls: Type, entity_name: str, entity_id: str, entity_data: Any) -> Dict[str, Any]:
    """Reusable handler for PUT endpoint."""
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"update_{entity_lower}")
    
    try:
        existing, warnings = await entity_cls.get(entity_id)
        # Add any warnings from get operation
        for warning in warnings:
            notify_warning(warning, NotificationType.DATABASE)
            
        # Merge payload data into existing entity and force validation
        update_dict = entity_data.model_dump(exclude_unset=True)
        updated = existing.model_copy(update=update_dict)
        
        # Force validation by recreating the model (triggers field validators)
        validated_updated = entity_cls.model_validate(updated.model_dump())
        result, save_warnings = await validated_updated.save()
        # Add any warnings from save operation
        for warning in save_warnings:
            notify_warning(warning, NotificationType.DATABASE)
        notify_success(f"{entity_name} updated successfully", NotificationType.BUSINESS)
        collection = end_notifications()
        return collection.to_entity_grouped_response(result.model_dump(), is_bulk=False)
    except NotFoundError as e:
        notify_error(f"{entity_name} not found", NotificationType.BUSINESS)
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    except (ValidationError, DuplicateError) as e:
        notify_validation_error(f"Failed to update {entity_lower}: {str(e)}")
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    except Exception as e:
        notify_error(f"Failed to update {entity_lower}: {str(e)}", NotificationType.SYSTEM)
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    finally:
        end_notifications()


async def delete_entity_handler(entity_cls: Type, entity_name: str, entity_id: str) -> Dict[str, Any]:
    """Reusable handler for DELETE endpoint."""
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"delete_{entity_lower}")
    
    try:
        success, warnings = await entity_cls.delete(entity_id)
        if success:
            notify_success(f"{entity_name} deleted successfully", NotificationType.BUSINESS)
        for warning in warnings:
            notify_warning(warning, NotificationType.DATABASE)
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    except NotFoundError:
        notify_error(f"{entity_name} not found", NotificationType.BUSINESS)
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    except Exception as e:
        notify_error(f"Failed to delete {entity_lower}: {str(e)}", NotificationType.SYSTEM)
        collection = end_notifications()
        return collection.to_entity_grouped_response(None, is_bulk=False)
    finally:
        end_notifications()