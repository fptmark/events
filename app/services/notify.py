"""
Simple static notification system with 3 types: errors, request_warnings, warnings.
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import HTTPException

class Error:
    SECURITY = 'security'    # Auth/authorization failures → 403
    REQUEST = 'request'      # Client request errors → 400  
    DATABASE = 'database'    # DB connection/operation failures → 500
    SYSTEM = 'system'        # Unhandled exceptions, infrastructure → 500

class Warning:
    NOT_FOUND = 'not_found'
    UNIQUE_VIOLATION = 'unique_violation'
    DATA_VALIDATION = 'data_validation'
    REQUEST = 'request'     # e.g. - bad sort field


class DuplicateConstraintError(Exception):
    """Raised when a unique constraint violation occurs - database agnostic"""
    
    def __init__(self, message: str, entity: str, field: str, entity_id: str = "new"):
        self.message = message
        self.entity = entity
        self.field = field
        self.entity_id = entity_id
        super().__init__(message)


class StopWorkError(HTTPException):
    """Single exception class for all stop-work scenarios"""
    def __init__(self, message: str, status_code: int, error_type: str):
        self.error_type = error_type  # For logging context
        super().__init__(status_code=status_code, detail=message)


class Notification:
    """Static notification collection system"""
    
    _errors: List[str] = []
    _warnings: Dict[str, Dict[str, List[Dict[str, str]]]] = {}  # Already in final format
    _request_warnings: List[Dict[str, str]] = []
    
    @classmethod
    def start(cls, entity: Optional[str] = None, operation: Optional[str] = None) -> None:
        """Start notification collection"""
        cls._errors.clear()
        cls._warnings.clear()
        cls._request_warnings.clear()
    
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
    def error(cls, stop_type: str, message: str, entity_type = None, field = None, raise_exception: bool = True) -> None:
        """Add stop-work error"""
        cls._errors.append(f"[{stop_type}] {message}")
        logging.error(f"[ERROR] {stop_type}: {message}")
        
        if raise_exception:
            # Determine HTTP status code based on error type
            if stop_type == Error.REQUEST:
                status_code = 400
            elif stop_type == Error.SECURITY:
                status_code = 403
            elif stop_type in [Error.DATABASE, Error.SYSTEM]:
                status_code = 500
            else:
                # Default to 500 for unknown types
                status_code = 500
            
            raise StopWorkError(message, status_code, stop_type)
    
    @classmethod
    def warning(cls, warning_type: str, message: str, entity_type = None, entity_id = None, field = None, value = None, parameter = None) -> None:
        """Add warning"""
        if parameter:
            # Request parameter warning - smart format: "[REQUEST] page: Invalid page number: abc"
            formatted_message = f"[{warning_type}] {parameter}: {message}"
            cls._request_warnings.append({"parameter": parameter, "message": formatted_message})
            logging.warning(f"[REQUEST WARNING] {formatted_message}")
        else:
            # Entity data warning - smart format based on available context
            entity_type = entity_type or "system"
            entity_id = entity_id or "general"
            
            # Smart message formatting
            if entity_type and entity_id and field:
                # "[DATA_VALIDATION] User:123 email: Invalid email format"
                formatted_message = f"[{warning_type}] {entity_type}:{entity_id} {field}: {message}"
                log_context = f"{entity_type}:{entity_id} {field}"
            elif entity_type and entity_id:
                # "[NOT_FOUND] User:123: Document not found"  
                formatted_message = f"[{warning_type}] {entity_type}:{entity_id}: {message}"
                log_context = f"{entity_type}:{entity_id}"
            elif entity_type:
                # "[UNIQUE_VIOLATION] User: Duplicate email address"
                formatted_message = f"[{warning_type}] {entity_type}: {message}"
                log_context = entity_type
            else:
                # "[DATA_VALIDATION] Missing required field"
                formatted_message = f"[{warning_type}] {message}"
                log_context = "System"
            
            # Initialize structure if needed
            if entity_type not in cls._warnings:
                cls._warnings[entity_type] = {}
            if entity_id not in cls._warnings[entity_type]:
                cls._warnings[entity_type][entity_id] = []
            
            # Add warning in final format
            warning_dict = {"message": formatted_message}
            if field:
                warning_dict["field"] = field
            cls._warnings[entity_type][entity_id].append(warning_dict)
            
            # Smart logging
            logging.warning(f"[WARNING] {log_context}: {formatted_message}")


    @classmethod
    def handle_duplicate_constraint(cls, error, is_validation=False):
        """Handle DuplicateConstraintError with context-sensitive behavior"""
        # Always add warning for UI field highlighting
        cls.warning(Warning.UNIQUE_VIOLATION, error.message, 
                   entity_type=error.entity, entity_id=error.entity_id, field=error.field)
        
        if not is_validation:
            # Data operations (create, update) - stop work
            cls.error(Error.REQUEST, f"Cannot save: {error.message}")
        # else: validation only - just continue with warning