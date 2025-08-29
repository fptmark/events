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
from app.routers.router_factory import ModelImportCache, EntityModelProtocol
from app.services.notification import Notification, ErrorType, WarningType
# Old error classes removed - using notification system instead
from app.services.request_context import RequestContext

logger = logging.getLogger(__name__)







async def get_all_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for GET ALL endpoint (paginated version)."""
    
    # Parse and normalize URL using RequestContext
    RequestContext.parse_request(str(request.url.path), dict(request.query_params))
    proper_entity_name = RequestContext.entity_type
    
    # Start notifications for this request
    Notification.start(entity=proper_entity_name, operation="list")
    
    try:
        # Get paginated data from model - pass RequestContext parameters  
        response = await entity_cls.get_all(
            RequestContext.sort_fields,
            RequestContext.filters,
            RequestContext.page,
            RequestContext.pageSize,
            RequestContext.view_spec
        )
        
        # End notifications and build success response
        notification_response = Notification.end()
        
        # Build response with correct structure: data, notifications, status
        final_response = {
            "data": response.get('data', []),
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "success")
        }
        
        # Add pagination metadata using total_records from factory
        if 'total_records' in response:
            from app.utils import pagination
            final_response.update(pagination(RequestContext.page, response['total_records'], RequestContext.pageSize))
        
        return final_response
        
    except Exception as e:
        Notification.error(ErrorType.SYSTEM, f"Failed to retrieve entities: {str(e)}")
        
        # End notifications and build error response
        notification_response = Notification.end()
        
        # Build error response with correct structure
        final_response = {
            "data": [],
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "failed")
        }
        
        # Add pagination metadata for error case
        from app.utils import pagination
        final_response.update(pagination(RequestContext.page, 0, RequestContext.pageSize))
        return final_response


async def get_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for GET endpoint."""
    
    # Parse and normalize URL using RequestContext
    RequestContext.parse_request(str(request.url.path), dict(request.query_params))
    proper_entity_name = RequestContext.entity_type
    
    # Start notifications for this request
    Notification.start(entity=proper_entity_name, operation="get")
    
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


async def create_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_data: BaseModel, request: Optional[Request] = None) -> Dict[str, Any]:
    """Reusable handler for POST endpoint."""
    
    # Parse and normalize URL using RequestContext (mainly for proper entity name)
    if request:
        RequestContext.parse_request(str(request.url.path), dict(request.query_params))
        proper_entity_name = RequestContext.entity_type
    else:
        proper_entity_name = entity_name
    
    # Start notifications for this request
    Notification.start(entity=proper_entity_name, operation="create")
    
    try:
        # Let model handle all validation and business logic
        entity = entity_cls(**entity_data.model_dump())
        result, warnings = await entity.save()
        # Note: Warnings are now added directly to notification system by model layer
        
        # End notifications and build response
        notification_response = Notification.end()
        
        return {
            "data": result.model_dump(),
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "success")
        }
        # Note: Validation errors are now handled by notification system in model layer
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        raise


async def update_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str, entity_data: BaseModel, request: Request = None) -> Dict[str, Any]:
    """Reusable handler for PUT endpoint - True PUT semantics (full replacement)."""
    
    # Parse and normalize URL using RequestContext (mainly for proper entity name)
    if request:
        RequestContext.parse_request(str(request.url.path), dict(request.query_params))
        proper_entity_name = RequestContext.entity_type
    else:
        proper_entity_name = entity_name
    
    # Start notifications for this request
    Notification.start(entity=proper_entity_name, operation="update")
    
    try:
        # True PUT semantics: validate complete entity data with URL's entity_id
        entity_dict = entity_data.model_dump()
        validated_entity = entity_cls.model_validate(entity_dict)
        
        # Save with entity_id from URL (authoritative) - this handles auto-fields internally
        result, save_warnings = await validated_entity.save(entity_id=entity_id)
        
        # Note: Warnings are now added directly to notification system by model layer
        
        # End notifications and build response
        notification_response = Notification.end()
        
        return {
            "data": result.model_dump(),
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "success")
        }
        # Note: Validation errors are now handled by notification system in model layer
    except Exception:
        # Let generic exceptions bubble up to FastAPI exception handler
        # which will return proper HTTP status code (500)
        raise


async def delete_entity_handler(entity_cls: Type[EntityModelProtocol], entity_name: str, entity_id: str, request: Request = None) -> Dict[str, Any]:
    """Reusable handler for DELETE endpoint."""
    
    # Parse and normalize URL using RequestContext (mainly for proper entity name)
    if request:
        RequestContext.parse_request(str(request.url.path), dict(request.query_params))
        proper_entity_name = RequestContext.entity_type
    else:
        proper_entity_name = entity_name
    
    # Start notifications for this request
    Notification.start(entity=proper_entity_name, operation="delete")
    
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