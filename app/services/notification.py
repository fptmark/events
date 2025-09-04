"""
Clean static notification system with clear separation between errors and warnings.

Errors: Stop-work conditions (database connection, security, system failures)
Warnings: Continue-work conditions (validation, business rules, not found)
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class ErrorType(Enum):
    """Stop-work error types"""
    DATABASE = "database"
    SYSTEM = "system"
    SECURITY = "security"
    APPLICATION = "application"


class WarningType(Enum):
    """Continue-work warning types"""
    VALIDATION = "validation"
    BUSINESS = "business"
    NOT_FOUND = "not_found"
    DUPLICATE = "duplicate"


@dataclass
class ErrorDetail:
    """System error that stops processing"""
    type: ErrorType
    message: str


@dataclass
class WarningDetail:
    """Entity warning that allows processing to continue"""
    type: WarningType
    message: str
    entity: Optional[str] = None
    entity_id: Optional[str] = None
    field: Optional[str] = None


class Notification:
    """Static notification collection system"""
    
    _errors: List[ErrorDetail] = []
    _warnings: List[WarningDetail] = []
    _active: bool = False
    
    @classmethod
    def start(cls, entity: Optional[str] = None, operation: Optional[str] = None) -> None:
        """Start notification collection"""
        cls._errors.clear()
        cls._warnings.clear()
        cls._active = True
    
    @classmethod
    def get(cls) -> Dict[str, Any]:
        """End collection and return formatted response"""
        if not cls._active:
            return {"status": "success"}
            
        # Build response
        if cls._errors:
            status = "error"
        elif cls._warnings:
            status = "warning"
        else:
            status = "success"
            
        response: Dict[str, Any] = {"status": status}
        
        # Add notifications if any exist
        if cls._errors or cls._warnings:
            notifications: Dict[str, Any] = {}
            
            # Errors as simple array
            if cls._errors:
                notifications["errors"] = [
                    {
                        "type": error.type.value,
                        "message": error.message
                    }
                    for error in cls._errors
                ]
            
            # Warnings grouped by entity/entity_id
            if cls._warnings:
                warnings_grouped: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
                for warning in cls._warnings:
                    entity_type = warning.entity or "system"
                    entity_id = warning.entity_id or "general"
                    
                    if entity_type not in warnings_grouped:
                        warnings_grouped[entity_type] = {}
                    if entity_id not in warnings_grouped[entity_type]:
                        warnings_grouped[entity_type][entity_id] = []
                    
                    warning_dict = {
                        "type": warning.type.value,
                        "message": warning.message
                    }
                    if warning.field:
                        warning_dict["field"] = warning.field
                        
                    warnings_grouped[entity_type][entity_id].append(warning_dict)
                
                notifications["warnings"] = warnings_grouped 
            
            response["notifications"] = notifications
        
        cls._active = False
        return response
    
    @classmethod
    def error(cls, error_type: ErrorType, message: str) -> None:
        """Add stop-work error"""
        if not cls._active:
            cls.start()
            
        error = ErrorDetail(type=error_type, message=message)
        cls._errors.append(error)
        
        # Log immediately
        logging.error(f"[ERROR] System [{error_type.value}] {message}")
    
    @classmethod
    def warning(
        cls, 
        warning_type: WarningType, 
        message: str,
        entity: Optional[str] = None,
        entity_id: Optional[str] = None,
        field: Optional[str] = None
    ) -> None:
        """Add continue-work warning"""
        if not cls._active:
            cls.start()
            
        warning = WarningDetail(
            type=warning_type,
            message=message,
            entity=entity,
            entity_id=entity_id,
            field=field
        )
        cls._warnings.append(warning)
        
        # Build log message
        entity_part = f"{entity}:{entity_id}" if entity and entity_id else entity or "System"
        field_part = f"{field} " if field else ""
        logging.warning(f"[WARNING] {entity_part} [{warning_type.value}] {field_part}{message}")
    
    @classmethod
    def has_errors(cls) -> bool:
        """Check if any stop-work errors exist"""
        return len(cls._errors) > 0
    
    @classmethod
    def has_warnings(cls) -> bool:
        """Check if any warnings exist"""
        return len(cls._warnings) > 0
    
    @classmethod
    def clear(cls) -> None:
        """Clear all notifications (for testing)"""
        cls._errors.clear()
        cls._warnings.clear()
        cls._active = False


# Convenience functions for common error types
def database_error(message: str) -> None:
    """Add database connection/operation error"""
    Notification.error(ErrorType.DATABASE, message)


def system_error(message: str) -> None:
    """Add system-level error"""
    Notification.error(ErrorType.SYSTEM, message)


def security_error(message: str) -> None:
    """Add security-related error"""
    Notification.error(ErrorType.SECURITY, message)


def application_error(message: str) -> None:
    """Add user-caused application error"""
    Notification.error(ErrorType.APPLICATION, message)


def validation_warning(message: str, entity: Optional[str] = None, entity_id: Optional[str] = None, field: Optional[str] = None) -> None:
    """Add validation warning"""
    Notification.warning(WarningType.VALIDATION, message, entity, entity_id, field)


def business_warning(message: str, entity: Optional[str] = None, entity_id: Optional[str] = None, field: Optional[str] = None) -> None:
    """Add business rule warning"""
    Notification.warning(WarningType.BUSINESS, message, entity, entity_id, field)


def not_found_warning(message: str, entity: Optional[str] = None, entity_id: Optional[str] = None) -> None:
    """Add not found warning"""
    Notification.warning(WarningType.NOT_FOUND, message, entity, entity_id)


def duplicate_warning(message: str, entity: Optional[str] = None, entity_id: Optional[str] = None, field: Optional[str] = None) -> None:
    """Add duplicate warning"""
    Notification.warning(WarningType.DUPLICATE, message, entity, entity_id, field)