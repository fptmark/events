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
        invalid_fields: List[ValidationFailure]
    ):
        self.message = message
        self.entity = entity
        self.invalid_fields = invalid_fields
        super().__init__(status_code=422, detail=message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": self.message,
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "invalid_fields": [
                    field.to_dict() for field in self.invalid_fields
                ]
            }
        }

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


def normalize_error_response(
    error: Union[Exception, RequestValidationError, str], 
    request_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Normalizes any error into a consistent FastAPI-compatible response format.
    
    Args:
        error: The error to normalize (custom exception, FastAPI validation error, or string)
        request_path: Optional request path to extract entity name
        
    Returns:
        Standardized error response dict with format: {"detail": {...}}
    """
    
    # Handle our custom error classes that already have to_dict()
    if hasattr(error, 'to_dict') and callable(getattr(error, 'to_dict')):
        # Use getattr to safely call to_dict() method
        to_dict_method = getattr(error, 'to_dict')
        result = to_dict_method()
        return result if isinstance(result, dict) else {"detail": {"message": str(error), "error_type": "UnknownError"}}
    
    # Handle FastAPI RequestValidationError
    if isinstance(error, RequestValidationError):
        failures = []
        for err in error.errors():
            field = err["loc"][-1] if err["loc"] else "unknown"
            failures.append(ValidationFailure(
                field=field,
                message=err["msg"],
                value=err.get("input")
            ))
        
        entity = None
        if request_path:
            entity = request_path.split("/")[-1]
            
        return {
            "detail": {
                "message": "Invalid request data",
                "error_type": "RequestValidationError",
                "entity": entity,
                "invalid_fields": [f.to_dict() for f in failures]
            }
        }
    
    # Handle string errors
    if isinstance(error, str):
        return {
            "detail": {
                "message": error,
                "error_type": "StringError"
            }
        }
    
    # Handle generic exceptions
    if isinstance(error, Exception):
        error_str = str(error).lower()
        
        # Check for specific error patterns and categorize
        if "index_not_found_exception" in error_str:
            entity = None
            if request_path:
                entity = request_path.split("/")[-1]
                
            return {
                "detail": {
                    "message": "Required index is missing: operation aborted",
                    "error_type": "IndexNotFoundError", 
                    "context": {
                        "error": str(error),
                        "entity": entity
                    }
                }
            }
        
        # Generic exception fallback
        return {
            "detail": {
                "message": "An unexpected error occurred",
                "error_type": error.__class__.__name__,
                "context": {
                    "error": str(error)
                }
            }
        }
    
    # Fallback for unknown error types
    return {
        "detail": {
            "message": "An unknown error occurred",
            "error_type": "UnknownError",
            "context": {
                "error": str(error)
            }
        }
    }