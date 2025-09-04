from typing import Dict, Any
from starlette.exceptions import HTTPException
from app.services.notification import database_error, system_error, security_error, application_error


class DatabaseError(HTTPException):
    """Error raised for database operations - true system failures only"""
    def __init__(self, message: str, entity: str, operation: str):
        self.message = message
        self.entity = entity
        self.operation = operation
        # Add to notification system
        database_error(message)
        super().__init__(status_code=500, detail=message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": self.message,
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "operation": self.operation
            }
        }


class SystemError(HTTPException):
    """Error raised for system-level failures"""
    def __init__(self, message: str, entity: str, operation: str):
        self.message = message
        self.entity = entity
        self.operation = operation
        # Add to notification system
        system_error(message)
        super().__init__(status_code=500, detail=message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": self.message,
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "operation": self.operation
            }
        }


class SecurityError(HTTPException):
    """Error raised for security violations"""
    def __init__(self, message: str, entity: str, operation: str):
        self.message = message
        self.entity = entity
        self.operation = operation
        # Add to notification system
        security_error(message)
        super().__init__(status_code=403, detail=message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": self.message,
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "operation": self.operation
            }
        }


class ApplicationError(HTTPException):
    """Error raised for user-caused application errors"""
    def __init__(self, message: str, entity: str, operation: str):
        self.message = message
        self.entity = entity
        self.operation = operation
        # Add to notification system
        application_error(message)
        super().__init__(status_code=400, detail=message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": self.message,
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "operation": self.operation
            }
        }


class DuplicateConstraintError(Exception):
    """Raised when a unique constraint violation occurs - database agnostic"""
    
    def __init__(self, message: str, entity: str, field: str, entity_id: str = "new"):
        self.message = message
        self.entity = entity
        self.field = field
        self.entity_id = entity_id
        super().__init__(message)
