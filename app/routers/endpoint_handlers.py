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
from pydantic_core import ValidationError as PydanticValidationError
from app.models.list_params import ListParams

logger = logging.getLogger(__name__)


class EntityModelProtocol(Protocol):
    """Protocol for entity model classes with required methods and attributes."""
    _metadata: Dict[str, Any]
    
    @classmethod
    async def get_list(cls, list_params=None, view_spec=None) -> Dict[str, Any]: ...
    
    @classmethod
    async def get(cls, entity_id: str, view_spec=None): ...
    
    async def save(self, entity_id: str = '') -> tuple: ...
    
    @classmethod
    async def delete(cls, entity_id: str) -> tuple[bool, list]: ...
    
    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> 'EntityModelProtocol': ...




async def list_all_entities_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for LIST endpoint (get all - now uses get_list with default pagination)."""
    
    # Start notifications for this request
    start_notifications(entity=entity_name, operation="list_all")
    
    # Extract query parameters for FK processing
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    try:
        # Use get_list with no list_params (defaults to page_size=100)
        response = await entity_cls.get_list(list_params=None, view_spec=view_spec)
        
        # End notifications and enhance response
        collection = end_notifications()
        enhanced_response = collection.to_entity_grouped_response(
            data=response.get('data'),
            is_bulk=True
        )
        # Copy all model response data (including pagination) to enhanced response
        enhanced_response.update(response)
        return enhanced_response

    except Exception as e:
        # Handle any errors in the processing
        notify_error(f"Error listing {entity_name}s: {str(e)}")
        # End notifications and enhance response even for errors
        collection = end_notifications()
        enhanced_response = collection.to_entity_grouped_response(data=[], is_bulk=True)
        # Add default pagination metadata for error case
        enhanced_response.update({
            "total_count": 0, 
            "page": 1, 
            "page_size": 100, 
            "total_pages": 0
        })
        return enhanced_response


async def list_entities_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for LIST endpoint (paginated version)."""
    
    # Start notifications for this request
    start_notifications(entity=entity_name, operation="list")
    
    # Extract query parameters
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    # Parse pagination/filtering parameters
    list_params = ListParams.from_query_params(query_params)
    
    try:
        # Get paginated data from model with FK processing (model handles all business logic)
        response = await entity_cls.get_list(list_params, view_spec=view_spec)
        
        # End notifications and enhance response
        collection = end_notifications()
        enhanced_response = collection.to_entity_grouped_response(
            data=response.get('data'),
            is_bulk=True
        )
        # Preserve all model response data (including pagination)
        for key, value in response.items():
            if key not in enhanced_response:
                enhanced_response[key] = value
        return enhanced_response
        
    except Exception as e:
        notify_error(f"Failed to retrieve entities: {str(e)}", NotificationType.SYSTEM, entity=entity_name)
        # End notifications and enhance response even for errors
        collection = end_notifications()
        enhanced_response = collection.to_entity_grouped_response(
            data=[], 
            is_bulk=True
        )
        # Add pagination metadata for error case
        enhanced_response.update({
            "total_count": 0, 
            "page": list_params.page, 
            "page_size": list_params.page_size, 
            "total_pages": 0
        })
        return enhanced_response


async def get_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for GET endpoint."""
    
    # Start notifications for this request
    start_notifications(entity=entity_name, operation="get")
    
    # Extract query parameters for FK processing
    query_params = dict(request.query_params)
    view_param = query_params.get('view')
    view_spec = json.loads(unquote(view_param)) if view_param else None
    
    try:
        # Get entity directly from model (now handles FK processing and view_spec)
        response = await entity_cls.get(entity_id, view_spec)
        
        # Add any warnings as notifications
        for warning in response.get("warnings", []):
            notify_warning(warning, NotificationType.DATABASE)
        
        # End notifications and enhance response
        collection = end_notifications()
        enhanced_response = collection.to_entity_grouped_response(
            data=response.get('data'),
            is_bulk=False
        )
        # Copy all model response data (including pagination) to enhanced response
        enhanced_response.update(response)
        return enhanced_response
        
    except NotFoundError:
        # Let the NotFoundError bubble up to FastAPI's exception handler
        # which will return a proper 404 response
        raise
    except Exception as e:
        notify_error(f"Failed to retrieve entity: {str(e)}", NotificationType.SYSTEM, entity=entity_name)
        # End notifications and enhance response even for errors
        collection = end_notifications()
        enhanced_response = collection.to_entity_grouped_response(data=None, is_bulk=False)
        return enhanced_response


async def create_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_data: BaseModel) -> Dict[str, Any]:
    """Reusable handler for POST endpoint."""
    
    # Start notifications for this request
    start_notifications(entity=entity_name, operation="create")
    
    try:
        # Let model handle all validation and business logic
        entity = entity_cls(**entity_data.model_dump())
        result, warnings = await entity.save()
        # Add any warnings from save operation
        for warning in warnings or []:
            notify_warning(warning, NotificationType.DATABASE)
        notify_success("Created successfully", NotificationType.BUSINESS, entity=entity_name)
        return {"data": result.model_dump()}
    except PydanticValidationError as e:
        # Convert Pydantic validation errors to notifications for middleware to handle
        for error in e.errors():
            field_name = str(error["loc"][-1]) if error.get("loc") else "unknown"
            notify_warning(
                message=error.get("msg", "Validation error"),
                type=NotificationType.VALIDATION,
                entity=entity_name,
                field_name=field_name,
                value=error.get("input"),
                operation="create"
            )
        # Convert to our custom ValidationError so middleware handles it properly
        from app.errors import ValidationFailure
        failures = [ValidationFailure(field_name=str(error["loc"][-1]), message=error["msg"], value=error.get("input")) for error in e.errors()]
        raise ValidationError(message="Validation failed", entity=entity_name, invalid_fields=failures)
    except (ValidationError, DuplicateError):
        # ValidationError and DuplicateError should be handled by middleware 
        # Let them bubble up so notifications are preserved in middleware response
        raise
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        raise


async def update_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str, entity_data: BaseModel) -> Dict[str, Any]:
    """Reusable handler for PUT endpoint - True PUT semantics (full replacement)."""
    
    # Start notifications for this request
    start_notifications(entity=entity_name, operation="update")
    
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
        return {"data": result.model_dump()}
    except PydanticValidationError as e:
        # Convert Pydantic validation errors to notifications for middleware to handle
        for error in e.errors():
            field_name = str(error["loc"][-1]) if error.get("loc") else "unknown"
            notify_warning(
                message=error.get("msg", "Validation error"),
                type=NotificationType.VALIDATION,
                entity=entity_name,
                field_name=field_name,
                value=error.get("input"),
                operation="update",
                entity_id=entity_id
            )
        # Convert to our custom ValidationError so middleware handles it properly
        from app.errors import ValidationFailure
        failures = [ValidationFailure(field_name=str(error["loc"][-1]), message=error["msg"], value=error.get("input")) for error in e.errors()]
        raise ValidationError(message="Validation failed", entity=entity_name, invalid_fields=failures)
    except (NotFoundError, ValidationError, DuplicateError):
        # Let these exceptions bubble up to FastAPI exception handlers
        # Middleware will handle the notifications properly
        raise
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        raise


async def delete_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str) -> Dict[str, Any]:
    """Reusable handler for DELETE endpoint."""
    
    # Start notifications for this request
    start_notifications(entity=entity_name, operation="delete")
    
    try:
        success, warnings = await entity_cls.delete(entity_id)
        if success:
            notify_success("Deleted successfully", NotificationType.BUSINESS, entity=entity_name)
        for warning in warnings or []:
            notify_warning(warning, NotificationType.DATABASE)
        return {"data": None}
    except NotFoundError:
        # Let NotFoundError bubble up to FastAPI exception handler
        # which will return proper HTTP status code (404)
        raise
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        raise