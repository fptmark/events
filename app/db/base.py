from abc import ABC, abstractmethod
from typing import Any, Dict, List, TypeVar, Type, Optional, Tuple, Callable
from pydantic import BaseModel
from functools import wraps
import hashlib
from ..errors import DatabaseError

T = TypeVar('T', bound=BaseModel)

class SyntheticDuplicateError(Exception):
    """Raised when synthetic index detects duplicate"""
    def __init__(self, collection: str, field: str, value: Any):
        self.collection = collection
        self.field = field
        self.value = value
        super().__init__(f"Synthetic duplicate constraint violation: {field} = {value} in {collection}")

class DatabaseInterface(ABC):
    """Base interface for database implementations"""
    
    def __init__(self):
        self._initialized = False
    
    def _ensure_initialized(self) -> None:
        """Ensure database is initialized, raise RuntimeError if not"""
        if not self._initialized:
            raise RuntimeError(f"{self.__class__.__name__} not initialized")
    
    def _handle_connection_error(self, error: Exception, database_name: str) -> None:
        """Handle connection errors with standardized DatabaseError"""
        raise DatabaseError(
            message=f"Failed to connect to {self.__class__.__name__}: {str(error)}",
            entity="connection", 
            operation="init"
        )
    
    def _wrap_database_operation(self, operation: str, entity: str):
        """Decorator to wrap database operations with error handling"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except DatabaseError:
                    # Re-raise existing DatabaseError with context preserved
                    raise
                except Exception as e:
                    raise DatabaseError(
                        message=str(e),
                        entity=entity,
                        operation=operation
                    )
            return wrapper
        return decorator
    
    @property
    @abstractmethod
    def id_field(self) -> str:
        """Get the ID field name for this database"""
        pass

    @abstractmethod
    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize the ID from a document"""
        pass

    @abstractmethod
    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize the database connection"""
        pass

    @abstractmethod
    async def get_all(self, collection: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Get all documents from a collection with count"""
        pass

    @abstractmethod
    async def get_by_id(self, collection: str, doc_id: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Get a document by ID"""
        pass

    @abstractmethod
    async def save_document(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Save a document to the database"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the database connection"""
        pass

    @abstractmethod
    async def collection_exists(self, collection: str) -> bool:
        """Check if a collection exists"""
        pass

    @abstractmethod
    async def create_collection(self, collection: str, indexes: List[Dict[str, Any]]) -> bool:
        """Create a collection with indexes"""
        pass

    @abstractmethod
    async def delete_collection(self, collection: str) -> bool:
        """Delete a collection"""
        pass

    @abstractmethod
    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document"""
        pass

    @abstractmethod
    async def list_collections(self) -> List[str]:
        """List all collections"""
        pass

    @abstractmethod
    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """
        List all indexes for a collection.
        
        Returns:
            List of index dictionaries with standardized format:
            {
                'name': str,           # Index name
                'fields': List[str],   # Field names in the index
                'unique': bool,        # Whether index enforces uniqueness
                'system': bool         # Whether it's a system index (like _id)
            }
        """
        pass

    @abstractmethod
    async def delete_index(self, collection: str, fields: List[str]) -> None:
        """Delete an index from a collection"""
        pass

    @abstractmethod
    async def supports_native_indexes(self) -> bool:
        """Check if database supports native unique indexes"""
        pass
    
    @abstractmethod
    async def document_exists_with_field_value(self, collection: str, field: str, value: Any, exclude_id: Optional[str] = None) -> bool:
        """Check if a document exists with the given field value (excluding optionally specified ID)"""
        pass
    
    # Optional method for databases that support single field index creation
    async def create_single_field_index(self, collection: str, field: str, index_name: str) -> None:
        """Create a single field index (optional - for synthetic index support)"""
        pass
    
    # Generic synthetic index methods (implemented in base class)
    async def prepare_document_for_save(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Dict[str, Any]:
        """Prepare document for save by adding synthetic hash fields if needed"""
        if not unique_constraints:
            return data
            
        # Check if database supports native indexes
        if await self.supports_native_indexes():
            return data  # Native indexes handle uniqueness
            
        return self._add_synthetic_hash_fields(data, unique_constraints)
    
    async def validate_unique_constraints_before_save(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> None:
        """Validate unique constraints before saving (works for both native and synthetic)"""
        if not unique_constraints:
            return
            
        # Check if database supports native indexes
        if await self.supports_native_indexes():
            return  # Native indexes will handle this during save
            
        # For synthetic indexes, validate manually
        await self._validate_synthetic_constraints(collection, data, unique_constraints)
    
    def _add_synthetic_hash_fields(self, data: Dict[str, Any], unique_constraints: List[List[str]]) -> Dict[str, Any]:
        """Add synthetic hash fields for multi-field unique constraints"""
        result = data.copy()
        
        for constraint_fields in unique_constraints:
            if len(constraint_fields) > 1:
                # Multi-field constraint - add hash field
                hash_field_name = self._get_hash_field_name(constraint_fields)
                values = [str(data.get(field, "")) for field in constraint_fields]
                hash_value = self._generate_constraint_hash(values)
                result[hash_field_name] = hash_value
        
        return result
    
    async def _validate_synthetic_constraints(self, collection: str, data: Dict[str, Any], unique_constraints: List[List[str]]) -> None:
        """Validate synthetic unique constraints"""
        document_id = data.get('id')
        
        for constraint_fields in unique_constraints:
            if len(constraint_fields) == 1:
                # Single field constraint
                field = constraint_fields[0]
                value = data.get(field)
                if value is not None and await self.document_exists_with_field_value(collection, field, value, document_id):
                    raise SyntheticDuplicateError(collection, field, value)
            else:
                # Multi-field constraint - check hash field
                hash_field_name = self._get_hash_field_name(constraint_fields)
                hash_value = data.get(hash_field_name)
                if hash_value and await self.document_exists_with_field_value(collection, hash_field_name, hash_value, document_id):
                    # Create user-friendly error message
                    field_desc = " + ".join(constraint_fields)
                    values = [str(data.get(field, "")) for field in constraint_fields]
                    value_desc = " + ".join(values)
                    raise SyntheticDuplicateError(collection, field_desc, value_desc)
    
    def _get_hash_field_name(self, fields: List[str]) -> str:
        """Generate consistent hash field name for multi-field constraints"""
        return "_".join(sorted(fields)) + "_hash"
    
    def _generate_constraint_hash(self, values: List[str]) -> str:
        """Generate consistent hash for multi-field constraints"""
        combined = "|".join(values)
        return hashlib.sha256(combined.encode()).hexdigest()

