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
from fastapi import Request, HTTPException
from pydantic import BaseModel

from app.services.notify import Notification
from app.services.request_context import RequestContext

logger = logging.getLogger(__name__)

class EntityModelProtocol(Protocol):
    """Protocol for entity model classes with required methods and attributes."""
    _metadata: Dict[str, Any]

    @classmethod
    async def get_all(cls, sort, filter, page: int, pageSize: int, view_spec) -> tuple: ...

    @classmethod
    async def get(cls, entity_id: str, view_spec) -> tuple: ...

    @classmethod
    async def create(cls, data: BaseModel, validate: bool = True) -> tuple: ...

    @classmethod
    async def update(cls, entity_id: str, data: BaseModel) -> tuple: ...

    @classmethod
    async def delete(cls, entity_id: str) -> tuple: ...

def parse_request_context(handler: Callable) -> Callable:
    """Decorator to parse RequestContext from request for all handlers."""
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        # Initialize notifications and reset the request params for each request
        Notification.start()
        RequestContext.reset()
        
        # Find request parameter
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        # Parse and normalize URL using RequestContext
        if request:
            # Convert entire query string to lowercase for case-insensitive handling
            lowercase_params = {}
            for key, value in request.query_params.items():
                lowercase_params[key.lower()] = value.lower()
            # Convert URL path to lowercase for case-insensitive handling
            lowercase_path = str(request.url.path).lower()
            RequestContext.parse_request(lowercase_path, lowercase_params)
        
        return await handler(*args, **kwargs)
    return wrapper


@parse_request_context
async def get_all_handler(entity_cls: Type[EntityModelProtocol], request: Request) -> Dict[str, Any]:
    """Reusable handler for GET ALL endpoint (paginated version)."""
    # Notification.start(entity=entity_cls.__name__, operation="get_all")

    # Model handles notifications internally, just call and return
    data, count = await entity_cls.get_all(
        RequestContext.sort_fields,
        RequestContext.filters,
        RequestContext.page,
        RequestContext.pageSize,
        RequestContext.view_spec
    )

    return update_response(data, count)


@parse_request_context
async def get_entity_handler(entity_cls: Type[EntityModelProtocol], entity_id: str, request: Request) -> Dict[str, Any]:
    """Reusable handler for GET endpoint."""
    # Notification.set(entity=entity_cls.__name__, operation="get")
    
    # Model handles notifications internally, just call and return
    response, _, _ = await entity_cls.get(entity_id, RequestContext.view_spec)
    
    return update_response(response)   


@parse_request_context
async def create_entity_handler(entity_cls: Type[EntityModelProtocol], entity_data: BaseModel, request: Request) -> Dict[str, Any]:
    """Reusable handler for POST endpoint."""
    # Model handles notifications internally, just call and return
    response, _ = await entity_cls.create(entity_data)
    return update_response(response)   

@parse_request_context
async def update_entity_handler(entity_cls: Type[EntityModelProtocol], entity_id: str, entity_data: BaseModel, request: Request) -> Dict[str, Any]:
    """Reusable handler for PUT endpoint - True PUT semantics (full replacement)."""
    # Model handles notifications internally, just call and return
    response, _ = await entity_cls.update(entity_id, entity_data)
    return update_response(response)


@parse_request_context
async def delete_entity_handler(entity_cls: Type[EntityModelProtocol], entity_id: str) -> Dict[str, Any]:
    """Reusable handler for DELETE endpoint."""
    # Notification.start(entity=entity_cls.__name__, operation="delete")

    # Model handles notifications internally, just call and return
    response, _ = await entity_cls.delete(entity_id)
    return update_response(response)


def update_response(data: Any, records: Optional[int] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    result['data'] = data

    if records is not None:
        totalPages = (records + RequestContext.pageSize - 1) // RequestContext.pageSize if records > 0 else 0
        result['pagination'] = {
            "page": RequestContext.page,
            "pageSize": RequestContext.pageSize,
            "total": records,
            "totalPages": totalPages
        }

    notification_response = Notification.get()
    notifications = notification_response.get("notifications", {})
    result["notifications"] = notifications

    # errors = notifications.get('errors', [])
    # warnings = notifications.get('warnings', {})
    result["status"] = notification_response.get('status', "missing")
    return result