from typing import List, Dict, Any, Optional

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

class ValidationError(Exception):
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
        super().__init__(message)
    
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

class NotFoundError(Exception):
    """Error raised when an entity is not found"""
    def __init__(self, entity: str, id: str):
        self.entity = entity
        self.id = id
        super().__init__(f"{entity} with id {id} not found")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": str(self),
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "id": self.id
            }
        }

class DuplicateError(ValidationError):
    """Error raised for duplicate values in unique fields"""
    def __init__(
        self, 
        entity: str,
        fields: List[str],
        values: Dict[str, Any]
    ):
        invalid_fields = [
            ValidationFailure(
                field=field,
                message="Value must be unique",
                value=values.get(field)
            )
            for field in fields
        ]
        super().__init__(
            message=f"Duplicate values found: {values}",
            entity=entity,
            invalid_fields=invalid_fields
        )

class DatabaseError(Exception):
    """Error raised for database operations"""
    def __init__(
        self, 
        message: str,
        entity: str,
        operation: str
    ):
        self.entity = entity
        self.operation = operation
        super().__init__(f"{entity} {operation} failed: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detail": {
                "message": str(self),
                "error_type": self.__class__.__name__,
                "entity": self.entity,
                "operation": self.operation
            }
        } 