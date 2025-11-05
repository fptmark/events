"""
Application-wide exception definitions.
Organized by concern: database operations, model/service operations, HTTP/application flow.
"""

from fastapi import HTTPException


# ==================== Database Layer Exceptions ====================

class DocumentNotFound(Exception):
    """Raised when a document is not found in the database."""

    def __init__(self, e=None, message=None):
        if message:
            super().__init__(message)
        elif e:
            super().__init__(str(e))
        else:
            super().__init__("Document not found")
        self.error = e
        self.message = message


class DatabaseError(Exception):
    """Raised for any database-specific errors (connection, operation failures, etc.)."""

    def __init__(self, e=None, message=None):
        if message:
            super().__init__(message)
        elif e:
            super().__init__(str(e))
        else:
            super().__init__("Database error")
        self.error = e
        self.message = message


class DuplicateConstraintError(Exception):
    """Raised when a unique constraint violation occurs - database agnostic.

    This exception is designed to work with Notification.handle_duplicate_constraint()
    which adds warnings and errors appropriately.
    """

    def __init__(self, message: str, entity = None, field = None, entity_id: str = "new"):
        self.message = message
        self.entity = entity
        self.field = field
        self.entity_id = entity_id
        super().__init__(message)


# ==================== Service Layer Exceptions ====================

class ModelNotFound(Exception):
    """Raised when a requested model class is not found"""

    def __init__(self, entity: str, message=None):
        self.entity = entity
        self.message = message or f"Model class not found for entity: {entity}"
        super().__init__(self.message)


# ==================== Application Flow Exceptions ====================

class StopWorkError(HTTPException):
    """Single exception class for all stop-work scenarios.

    Caught by main.py exception handler and converted to appropriate HTTP response.
    Raised by Notification.error() to halt execution and return error to client.
    """

    def __init__(self, message: str, status_code: int, error_type: str,
                 entity = None, field = None, value = None):
        self.error_type = error_type  # For logging context
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(status_code=status_code, detail=message)
