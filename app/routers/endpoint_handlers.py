"""
Reusable CRUD endpoint handlers for dynamic router creation.

This module contains the core CRUD endpoint logic that can be reused
across different entity routers, including FK data processing and
notification handling.
"""

import json
import logging
import inspect
from typing import Dict, Any, Type, Optional, Union, Protocol
from urllib.parse import unquote
from fastapi import Request
from pydantic import BaseModel

from app.config import Config
from app.routers.router_factory import ModelImportCache
from app.notification import (
    start_notifications, end_notifications,
    notify_success, notify_error, notify_warning, notify_validation_error,
    NotificationType
)
from app.errors import ValidationError, NotFoundError, DuplicateError
from app.models.list_params import ListParams

logger = logging.getLogger(__name__)


class EntityModelProtocol(Protocol):
    """Protocol for entity model classes with required methods and attributes."""
    _metadata: Dict[str, Any]
    
    @classmethod
    async def get_all(cls) -> Dict[str, Any]: ...
    
    @classmethod
    async def get_list(cls, list_params) -> Dict[str, Any]: ...
    
    @classmethod
    async def get(cls, entity_id: str): ...
    
    async def save(self, entity_id: str = '') -> tuple: ...
    
    @classmethod
    async def delete(cls, entity_id: str) -> tuple[bool, list]: ...
    
    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> 'EntityModelProtocol': ...




async def list_all_entities_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for LIST endpoint (get all - legacy version)."""
    
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"list_{entity_lower}s")
    
    # Extract query parameters for FK processing
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    try:
        # Get data from model with FK processing (model handles all business logic)
        response = await entity_cls.get_all(view_spec=view_spec)

    except Exception as e:
        # Handle any errors in the processing
        notify_error(f"Error listing {entity_name}s: {str(e)}")
        response = {"data": []}
    finally:
        # Add notifications to response
        collection = end_notifications()
        return collection.to_entity_grouped_response(data=response['data'], is_bulk=True)


async def list_entities_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for LIST endpoint (paginated version)."""
    
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"list_{entity_lower}s")
    
    # Extract query parameters
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    # Parse pagination/filtering parameters
    list_params = ListParams.from_query_params(query_params)
    
    try:
        # Get paginated data from model with FK processing (model handles all business logic)
        response = await entity_cls.get_list(list_params, view_spec=view_spec)
        
        collection = end_notifications()
        return collection.to_entity_grouped_response(data=response['data'], is_bulk=True)
    except Exception as e:
        notify_error(f"Failed to retrieve entities: {str(e)}", NotificationType.SYSTEM, entity=entity_name)
        collection = end_notifications()
        return collection.to_entity_grouped_response(data=[], is_bulk=True)
    finally:
        end_notifications()


async def get_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for GET endpoint."""
    
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"get_{entity_lower}")
    
    # Extract query parameters for FK processing
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    try:
        # Get entity with FK processing (model handles all business logic)
        from app.models.utils import get_entity_with_fk
        response = await get_entity_with_fk(entity_cls, entity_id, view_spec)
        
        # Add any warnings as notifications
        for warning in response.get("warnings", []):
            notify_warning(warning, NotificationType.DATABASE)
        
        collection = end_notifications()
        return collection.to_entity_grouped_response(response['data'], is_bulk=False)
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


async def create_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_data: BaseModel) -> Dict[str, Any]:
    """Reusable handler for POST endpoint."""
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"create_{entity_lower}")
    
    try:
        # Let model handle all validation and business logic
        entity = entity_cls(**entity_data.model_dump())
        result, warnings = await entity.save()
        # Add any warnings from save operation
        for warning in warnings or []:
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


async def update_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str, entity_data: BaseModel) -> Dict[str, Any]:
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
        for warning in save_warnings or []:
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


async def delete_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str) -> Dict[str, Any]:
    """Reusable handler for DELETE endpoint."""
    entity_lower = entity_name.lower()
    notifications = start_notifications(entity=entity_name, operation=f"delete_{entity_lower}")
    
    try:
        success, warnings = await entity_cls.delete(entity_id)
        if success:
            notify_success("Deleted successfully", NotificationType.BUSINESS, entity=entity_name)
        for warning in warnings or []:
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