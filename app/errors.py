from typing import List, Dict, Any, Optional, Union
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

class ValidationFailure:
    """Represents a single field validation failure"""
    def __init__(self, field: str, message: str, value: Any):
        self.field = field
        self.message = message
        self.value = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
            "value": self.value
        }

class ValidationError(HTTPException):
    """Base validation error with support for multiple field failures"""
    def __init__(
        self, 
        message: str,
        entity: str,
        invalid_fields: List[ValidationFailure],
        entity_id: Optional[str] = None
    ):
        self.message = message
        self.entity = entity
        self.invalid_fields = invalid_fields
        self.entity_id = entity_id
        super().__init__(status_code=422, detail=message)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "detail": {
                "message": self.message,
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "invalid_fields": [
                    field.to_dict() for field in self.invalid_fields
                ]
            }
        }
        if self.entity_id:
            result["detail"]["entity_id"] = self.entity_id
        return result

class NotFoundError(HTTPException):
    """Error raised when an entity is not found"""
    def __init__(self, entity: str, id: str):
        self.entity = entity
        self.id = id
        self.message = f"{entity} with ID {id} was not found"
        super().__init__(status_code=404, detail=self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": str(self),
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "id": self.id
            }
        }

class DuplicateError(HTTPException):
    """Error raised for duplicate values in unique fields"""
    def __init__(self, entity: str, field: str, value: Any):
        self.entity = entity
        self.field = field
        self.value = value
        self.message = f"Duplicate {field} value '{value}' found in {entity}"
        super().__init__(status_code=409, detail=self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": str(self),
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "field": self.field,
                "value": self.value
            }
        }

class DatabaseError(HTTPException):
    """Error raised for database operations"""
    def __init__(
        self, 
        message: str,
        entity: str,
        operation: str
    ):
        self.message = message
        self.entity = entity
        self.operation = operation
        super().__init__(status_code=500, detail=f"Database error in {entity}.{operation}: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": str(self),
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "operation": self.operation
            }
        }
