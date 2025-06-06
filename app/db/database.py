from typing import TypeVar, Type, ClassVar, Optional, Any, Dict, Sequence
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class Database:
    """Database abstraction layer that handles database operations."""
    
    # Class variable for the ID field name - can be changed per implementation
    ID_FIELD: ClassVar[str] = "_id"
    
    @classmethod
    def get_id_field(cls) -> str:
        """Get the database-specific ID field name"""
        return cls.ID_FIELD

    @classmethod
    async def find_all(cls, collection: str, model_cls: Type[T]) -> Sequence[T]:
        """Find all documents in a collection"""
        # Implementation will vary by database
        raise NotImplementedError()

    @classmethod
    async def get_by_id(cls, collection: str, id: str, model_cls: Type[T]) -> Optional[T]:
        """Get a document by ID"""
        # Implementation will vary by database
        raise NotImplementedError()

    @classmethod
    async def save_document(cls, collection: str, id: Optional[str], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Save a document (create or update)"""
        # Implementation will vary by database
        raise NotImplementedError()

    @classmethod
    async def delete_document(cls, collection: str, id: str) -> bool:
        """Delete a document by ID"""
        # Implementation will vary by database
        raise NotImplementedError() 