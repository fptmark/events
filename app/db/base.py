from abc import ABC, abstractmethod
from typing import Any, Dict, List, TypeVar, Type, Optional, Tuple
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class DatabaseInterface(ABC):
    """Base interface for database implementations"""
    
    @property
    @abstractmethod
    def id_field(self) -> str:
        """Get the ID field name for this database"""
        pass

    @abstractmethod
    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize the database connection"""
        pass

    @abstractmethod
    async def get_all(self, collection: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Get all documents from a collection"""
        pass

    @abstractmethod
    async def get_by_id(self, collection: str, doc_id: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Get a document by ID"""
        pass

    @abstractmethod
    async def save_document(self, collection: str, doc_id: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
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

