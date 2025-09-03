"""
Reusable CRUD endpoint handlers for dynamic router creation.

This module contains the core CRUD endpoint logic that can be reused
across different entity routers, including FK data processing and
notification handling.
"""

import json
import logging
import inspect
from typing import Dict, Any, Type, Optional, Union, Protocol, Callable
from urllib.parse import unquote
from functools import wraps
from fastapi import Request
from pydantic import BaseModel

from app.routers.router_factory import EntityModelProtocol
from app.services.notification import Notification, ErrorType, validation_warning
from app.services.request_context import RequestContext

logger = logging.getLogger(__name__)


def parse_request_context(handler: Callable) -> Callable:
    """Decorator to parse RequestContext from request for all handlers."""
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        # Find request parameter
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        # Parse and normalize URL using RequestContext
        if request:
            RequestContext.parse_request(str(request.url.path), dict(request.query_params))
        
        return await handler(*args, **kwargs)
    return wrapper


@parse_request_context
async def get_all_handler(entity_cls: Type[EntityModelProtocol]) -> Dict[str, Any]:
    """Reusable handler for GET ALL endpoint (paginated version)."""
    
    # Start notifications for this request
    Notification.start(entity=RequestContext.entity_type, operation="get_all")
    
    try:
        # Get paginated data from model - pass RequestContext parameters  
        response = await entity_cls.get_all(
            RequestContext.sort_fields,
            RequestContext.filters,
            RequestContext.page,
            RequestContext.pageSize,
            RequestContext.view_spec
        )
        
    except Exception as e:
        Notification.error(ErrorType.SYSTEM, f"Failed to retrieve entities: {str(e)}")
        
    # End notifications and build response
    notification_response = Notification.end()
        
    total_records = response.get('total_records', 0) if response else 0
    notifications = notification_response.get("notifications", {})
    if notifications.get("errors", []):
        status = "error"
    elif notifications.get("warnings", {}):
        status = "warning"
    else:
        status = "success"

    # Build error response with correct structure
    final_response = {
        "data": response.get('data', []),
        "notifications": notifications,
        "status": status #notification_response.get("status", "failed")
    }
        
    # Add pagination metadata under pagination key
    # final_response["pagination"] = pagination(RequestContext.page, total_records, RequestContext.pageSize)
    return final_response


@parse_request_context
async def get_entity_handler(entity_cls: Type[EntityModelProtocol], entity_id: str) -> Dict[str, Any]:
    """Reusable handler for GET endpoint."""
    
    # Start notifications for this request
    Notification.start(entity=RequestContext.entity_type, operation="get")
    
    try:
        # Get entity directly from model - pass RequestContext parameters
        response = await entity_cls.get(entity_id, RequestContext.view_spec)
        
        # Note: Warnings are now added directly to notification system by model layer
        
        # End notifications and build response following response.json structure
        notification_response = Notification.end()
        
        # Build response with correct structure: data, notifications, status
        final_response = {
            "data": response.get('data'),
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "success")
        }
        return final_response
        
    except Exception as e:
        Notification.error(ErrorType.SYSTEM, f"Failed to retrieve entity: {str(e)}")
        # End notifications and build error response following response.json structure
        notification_response = Notification.end()
        
        # Build error response with correct structure
        final_response = {
            "data": None,
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "failed")
        }
        return final_response


@parse_request_context
async def create_entity_handler(entity_cls: Type[EntityModelProtocol], entity_data: BaseModel) -> Dict[str, Any]:
    """Reusable handler for POST endpoint."""
    
    # Start notifications for this request
    Notification.start(entity=RequestContext.entity_type, operation="create")
    
    try:
        # Let model handle all validation and business logic
        result = await entity_cls.create(entity_data.model_dump())
        # Note: Warnings are now added directly to notification system by model layer
        
        # End notifications and build response
        notification_response = Notification.end()
        
        return {
            "data": result,
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "success")
        }
        # Note: Validation errors are now handled by notification system in model layer
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        raise


@parse_request_context
async def update_entity_handler(entity_cls: Type[EntityModelProtocol], entity_data: BaseModel) -> Dict[str, Any]:
    """Reusable handler for PUT endpoint - True PUT semantics (full replacement)."""
    
    # Start notifications for this request
    Notification.start(entity=RequestContext.entity_type, operation="update")
    
    try:
        # True PUT semantics: validate complete entity data with URL's entity_id
        entity_dict = entity_data.model_dump()
        if 'id' not in entity_dict or not entity_dict['id']:
            validation_warning(
                message="Missing 'id' field in request body for update operation",
                entity=RequestContext.entity_type,
                entity_id="missing",
                field="id"
            )
            return {
                "data": entity_dict,
                "notifications": Notification.end().get("notifications", {}),
                "status": "warning"
            }
        
        # Let model handle all validation and business logic
        result = await entity_cls.update(entity_dict)
        
        # Note: Warnings are now added directly to notification system by model layer
        
        # End notifications and build response
        notification_response = Notification.end()
        
        return {
            "data": result,
            "notifications": notification_response.get("notifications", {}),
            "status": "success"
        }
        # Note: Validation errors are now handled by notification system in model layer
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        raise


@parse_request_context
async def delete_entity_handler(entity_cls: Type[EntityModelProtocol], entity_id: str) -> Dict[str, Any]:
    """Reusable handler for DELETE endpoint."""
    
    # Start notifications for this request
    Notification.start(entity=RequestContext.entity_type, operation="delete")
    
    try:
        success = await entity_cls.delete(entity_id)
        # Note: Warnings are now added directly to notification system by model layer
        
        # End notifications and build response
        notification_response = Notification.end()
        
        return {
            "data": None,
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "success")
        }
        # Note: Not found errors are now handled by notification system in model layer
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        raise