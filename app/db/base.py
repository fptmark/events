from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class DatabaseInterface(ABC):
    """
    Abstract base class for database implementations.
    
    Provides a consistent interface for different database backends
    (Elasticsearch, MongoDB, etc.) allowing runtime selection.
    """

    @property
    @abstractmethod
    def id_field(self) -> str:
        """
        Get the database-specific ID field name.
        
        Returns:
            str: The field name used for document IDs (e.g., "_id" for ES/Mongo, "id" for SQL)
        """
        pass

    @abstractmethod
    async def init(self, connection_str: str, database_name: str) -> None:
        """
        Initialize database connection.
        
        Args:
            connection_str: Database connection string/URL
            database_name: Name of the database/index to use
            
        Raises:
            DatabaseError: If connection fails
        """
        pass

    @abstractmethod
    async def find_all(self, collection: str, model_cls: Type[T]) -> List[T]:
        """
        Find all documents in a collection.
        
        Args:
            collection: Collection/index name
            model_cls: Pydantic model class for validation
            
        Returns:
            List of validated model instances
            
        Raises:
            DatabaseError: If query fails
            ValidationError: If document validation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, collection: str, doc_id: str, model_cls: Type[T]) -> Optional[T]:
        """
        Get a document by its ID.
        
        Args:
            collection: Collection/index name
            doc_id: Document ID
            model_cls: Pydantic model class for validation
            
        Returns:
            Validated model instance or None if not found
            
        Raises:
            DatabaseError: If query fails
            ValidationError: If document validation fails
        """
        pass

    @abstractmethod
    async def save_document(self, collection: str, doc_id: Optional[str], 
                           data: Dict[str, Any]) -> Any:
        """
        Save a document to the database.
        
        Args:
            collection: Collection/index name
            doc_id: Document ID (None for auto-generation)
            data: Document data to save
            
        Returns:
            Database-specific response object
            
        Raises:
            DatabaseError: If save operation fails
            ValidationError: If required collection/index doesn't exist
        """
        pass

    @abstractmethod
    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """
        Delete a document from the database.
        
        Args:
            collection: Collection/index name
            doc_id: Document ID to delete
            
        Returns:
            True if document was deleted, False if not found
            
        Raises:
            DatabaseError: If delete operation fails
        """
        pass

    @abstractmethod
    async def check_unique_constraints(self, collection: str, constraints: List[List[str]], 
                                     data: Dict[str, Any], exclude_id: Optional[str] = None) -> List[str]:
        """
        Check uniqueness constraints against existing documents.
        
        Args:
            collection: Collection/index name
            constraints: List of field combinations that must be unique
                        e.g., [['email'], ['username'], ['firstName', 'lastName']]
            data: Document data to check
            exclude_id: Document ID to exclude from check (for updates)
            
        Returns:
            List of field names that have conflicts (empty if no conflicts)
            
        Raises:
            DatabaseError: If constraint check fails
        """
        pass

    @abstractmethod
    async def exists(self, collection: str, doc_id: str) -> bool:
        """
        Check if a document exists.
        
        Args:
            collection: Collection/index name
            doc_id: Document ID to check
            
        Returns:
            True if document exists, False otherwise
            
        Raises:
            DatabaseError: If existence check fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close database connections and cleanup resources.
        
        Should be called during application shutdown.
        """
        pass

    def validate_document(self, doc_data: Dict[str, Any], model_cls: Type[T]) -> T:
        """
        Validate document data against a Pydantic model.
        
        This is a common operation across all database implementations,
        so it's provided as a concrete method in the base class.
        
        Args:
            doc_data: Raw document data from database
            model_cls: Pydantic model class for validation
            
        Returns:
            Validated model instance
            
        Raises:
            ValidationError: If validation fails
        """
        from pydantic import ValidationError as PydanticValidationError
        from ..errors import ValidationError, ValidationFailure
        
        try:
            return model_cls.model_validate(doc_data)
        except PydanticValidationError as e:
            # Convert Pydantic validation error to our standard format
            errors = e.errors()
            if errors:
                failures = [
                    ValidationFailure(
                        field=str(err["loc"][-1]),
                        message=err["msg"],
                        value=err.get("input")
                    )
                    for err in errors
                ]
                raise ValidationError(
                    message="Validation failed",
                    entity=model_cls.__name__,
                    invalid_fields=failures
                )
            raise ValidationError(
                message="Validation failed",
                entity=model_cls.__name__,
                invalid_fields=[]
            )