"""
Simple static notification system with 3 types: errors, request_warnings, warnings.
"""

import logging
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
from fastapi import HTTPException

from app.exceptions import DuplicateConstraintError, StopWorkError


class HTTP:
    """HTTP status codes for errors"""
    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE = 422

    # 5xx Server Errors
    INTERNAL_ERROR = 500


def get_error_category(status_code: int) -> str:
    """Get human-readable category name for logging from HTTP status code"""
    return {
        400: 'bad_request',
        401: 'unauthorized',
        403: 'forbidden',
        404: 'not_found',
        409: 'conflict',
        422: 'validation_failed',
        500: 'internal_error',
    }.get(status_code, f'http_{status_code}')

class Warning:
    NOT_FOUND = 'not_found'
    UNIQUE_VIOLATION = 'unique_violation'
    DATA_VALIDATION = 'validation'
    REQUEST = 'request'     # e.g. - bad sort field
    BAD_NAME = 'bad_name'   # unknown entity or field
    MISSING = 'missing'


class Notification:
    """Static notification collection system"""
    
    _errors: List[str] = []
    _warnings: Dict[str, Dict[str, List[Dict[str, str]]]] = {}  # Already in final format
    _request_warnings: List[Dict[str, str]] = []
    _suppress_warnings: bool = False
    
    @classmethod
    def start(cls) -> None:
        """Start notification collection"""
        cls._errors.clear()
        cls._warnings.clear()
        cls._request_warnings.clear()
    
    @classmethod
    @contextmanager
    def suppress_warnings(cls):
        """Context manager to suppress warning notifications during FK lookups"""
        old_value = cls._suppress_warnings
        cls._suppress_warnings = True
        try:
            yield
        finally:
            cls._suppress_warnings = old_value
    
    @classmethod
    def get(cls) -> Dict[str, Any]:
        """Return formatted response"""
        # Build response
        if cls._errors:
            status = "error"
        elif cls._warnings or cls._request_warnings:
            status = "warning"
        else:
            status = "success"
            
        response: Dict[str, Any] = {"status": status}
        
        # Add notifications if any exist
        if cls._errors or cls._warnings or cls._request_warnings:
            notifications: Dict[str, Any] = {}
            
            if cls._errors:
                notifications["errors"] = [{"message": error} for error in cls._errors]
            
            if cls._warnings:
                notifications["warnings"] = cls._warnings
            
            if cls._request_warnings:
                notifications["request_warnings"] = cls._request_warnings
            
            response["notifications"] = notifications
        
        return response
    
    @classmethod
    def error(cls, status_code: int, message: str, entity: Optional[str] = None, field: Optional[str] = None, value: Optional[str] = None, raise_exception: bool = True) -> None:
        """
        Add stop-work error and raise StopWorkError with HTTP status code.

        Args:
            status_code: HTTP status code (use HTTP.NOT_FOUND, HTTP.BAD_REQUEST, etc.)
            message: Error message
            entity: Entity name (optional, for context)
            field: Field name (optional, for validation errors)
            value: Field value (optional, for validation errors)
            raise_exception: If True, raises StopWorkError immediately
        """
        category = get_error_category(status_code)
        cls._errors.append(f"[{category}] {message}")
        logging.error(f"[{status_code}] {message}")

        if raise_exception:
            raise StopWorkError(message, status_code, category, entity=entity, field=field, value=value)
    
    @classmethod
    def request_warning(cls, message:str = '', entity:str = '', field:str = '', value:str = '', parameter:str = ''):
        cls.warning(Warning.REQUEST, message=message, entity=entity, field=field, value=value, parameter=parameter)

    @classmethod
    def warning(cls, warning_type: str, message: str = '', entity:str = '', entity_id:str = '', field:str = '', value = None, parameter:str = '') -> None:
        """Add warning"""
        # Skip warnings if suppressed (e.g., during FK lookups)
        if cls._suppress_warnings:
            return
            
        warning = {'type': warning_type}
        if warning_type == Warning.REQUEST:
            if message:
                warning['message'] = message
            if value:
                warning['value'] = value
            if len(entity) > 0:
                warning['entity'] = entity
            if len(field) > 0:
                warning['field'] = field
            if parameter:
                warning['parameter'] = parameter
            cls._request_warnings.append(warning)

        else:
            # entity = entity or 'system'
            # entity_id = entity_id or 'general'
            warning['entity'] = entity
            warning['entity_id'] = entity_id
            warning['message'] = message
        
            if field:
                warning['field'] = field
            if value:
                warning['value'] = value
            if parameter:
                warning['parameter'] = parameter
            
            # Initialize structure if needed
            if entity not in cls._warnings:
                cls._warnings[entity] = {}
            if entity_id not in cls._warnings[entity]:
                cls._warnings[entity][entity_id] = []
            
            cls._warnings[entity][entity_id].append(warning)
            
        # Log the warning
        logging.warning(warning)


    @classmethod
    def handle_duplicate_constraint(cls, error, is_validation=False):
        """Handle DuplicateConstraintError with context-sensitive behavior"""
        # Always add warning for UI field highlighting
        cls.warning(Warning.UNIQUE_VIOLATION, error.message,
                   entity=error.entity, entity_id=error.entity_id, field=error.field)

        if not is_validation:
            # Data operations (create, update) - stop work with 409 Conflict
            cls.error(HTTP.CONFLICT, f"Cannot save: {error.message}",
                     entity=error.entity, field=error.field)
        # else: validation only - just continue with warning