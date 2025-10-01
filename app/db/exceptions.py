"""
Database-specific exceptions for consistent error handling across all drivers.
"""


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
    """Raised when a unique constraint is violated."""

    def __init__(self, e=None, message=None):
        if message:
            super().__init__(message)
        elif e:
            super().__init__(str(e))
        else:
            super().__init__("Duplicate constraint violation")
        self.error = e
        self.message = message


class ModelNotFound(Exception):
    """Raised when a requested model class is not found"""

    def __init__(self, entity_type: str, message=None):
        self.entity_type = entity_type
        self.message = message or f"Model class not found for entity type: {entity_type}"
        super().__init__(self.message)