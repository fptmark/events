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
    async def initialize_indexes(self) -> None:
        """
        Initialize database indexes based on model metadata.
        This method will:
        1. Discover required indexes from model metadata
        2. Create missing indexes
        3. Remove unused indexes
        4. Skip system indexes
        
        This is a non-destructive operation - it will not delete any collections or data,
        only manage indexes.
        
        Raises:
            DatabaseError: If index initialization fails
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
    async def save_document(self, collection: str, doc_id: Optional[Any], data: Dict[str, Any], 
                          unique_constraints: Optional[List[List[str]]] = None) -> Any:
        """
        Save a document to the database.
        
        Args:
            collection: Collection/index name
            doc_id: Document ID (optional)
            data: Document data to save
            unique_constraints: List of field combinations that must be unique
                              e.g., [['email'], ['username'], ['firstName', 'lastName']]
            
        Returns:
            Result of save operation (implementation specific)
            
        Raises:
            DatabaseError: If save fails
            ValidationError: If unique constraints are violated
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

    @abstractmethod
    async def list_collections(self) -> List[str]:
        """
        List all collections/indexes in the database.
        
        Returns:
            List of collection/index names
            
        Raises:
            DatabaseError: If listing fails
        """
        pass

    @abstractmethod
    async def create_collection(self, collection: str, **kwargs) -> bool:
        """
        Create a collection/index with optional settings.
        
        Args:
            collection: Collection/index name to create
            **kwargs: Database-specific settings (mappings, shards, etc.)
            
        Returns:
            True if created successfully, False if already exists
            
        Raises:
            DatabaseError: If creation fails
        """
        pass

    @abstractmethod
    async def delete_collection(self, collection: str) -> bool:
        """
        Delete a collection/index.
        
        Args:
            collection: Collection/index name to delete
            
        Returns:
            True if deleted successfully, False if didn't exist
            
        Raises:
            DatabaseError: If deletion fails
        """
        pass

    @abstractmethod
    async def collection_exists(self, collection: str) -> bool:
        """
        Check if a collection/index exists.
        
        Args:
            collection: Collection/index name to check
            
        Returns:
            True if collection exists, False otherwise
            
        Raises:
            DatabaseError: If check fails
        """
        pass

    @abstractmethod
    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """
        List all indexes for a specific collection.
        
        Args:
            collection: Collection name to get indexes for
            
        Returns:
            List of index definitions with names and fields
            
        Raises:
            DatabaseError: If listing fails
        """
        pass

    @abstractmethod
    async def create_index(self, collection: str, fields: List[str], unique: bool = False, **kwargs) -> bool:
        """
        Create an index on specific fields.
        
        Args:
            collection: Collection name
            fields: List of field names to index
            unique: Whether this should be a unique index
            **kwargs: Database-specific index options
            
        Returns:
            True if created successfully, False if already exists
            
        Raises:
            DatabaseError: If creation fails
        """
        pass

    @abstractmethod
    async def delete_index(self, collection: str, index_name: str) -> bool:
        """
        Delete a specific index.
        
        Args:
            collection: Collection name
            index_name: Name of index to delete
            
        Returns:
            True if deleted successfully, False if didn't exist
            
        Raises:
            DatabaseError: If deletion fails
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