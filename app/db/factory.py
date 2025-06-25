from typing import Any, Dict, List, Optional, Type, TypeVar, cast, Tuple
import logging
from pydantic import BaseModel
from bson import ObjectId

from .base import DatabaseInterface, T
from .elasticsearch import ElasticsearchDatabase
from .mongodb import MongoDatabase
from ..errors import DatabaseError
from ..notification import notify_warning, notify_database_error, NotificationType

class DatabaseFactory:
    """
    Factory class for creating and managing database instances.
    
    Supports runtime selection of database backends and maintains
    a singleton instance for the application.
    """
    
    _instance: Optional[DatabaseInterface] = None
    _db_type: Optional[str] = None
    _id_field: str = "_id"  # Default to MongoDB's ID field

    @classmethod
    async def initialize(cls, db_type: str, connection_str: str, database_name: str) -> DatabaseInterface:
        db: DatabaseInterface
        """Initialize database connection."""
        if cls._instance is not None:
            logging.info("DatabaseFactory: Already initialized")
            return cls._instance
            
        try:
            if db_type.lower() == "mongodb":
                db = MongoDatabase()
            elif db_type.lower() == "elasticsearch":
                db = ElasticsearchDatabase()
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
                
            await db.init(connection_str, database_name)
            cls._instance = db
            cls._db_type = db_type
            return db
            
        except Exception as e:
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(
                message=f"Failed to initialize database: {str(e)}",
                entity="connection",
                operation="initialize"
            )

    @classmethod
    def get_instance(cls) -> DatabaseInterface:
        """Get the database instance."""
        if cls._instance is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def set_instance(cls, instance: DatabaseInterface, db_type: str) -> None:
        """
        Set the current database instance.
        
        Args:
            instance: Database instance to set
            db_type: Type of database for logging/debugging
        """
        cls._instance = instance
        cls._db_type = db_type
        logging.info(f"Database instance set to: {db_type}")

    @classmethod
    def get_db_type(cls) -> Optional[str]:
        """
        Get the currently configured database type.
        
        Returns:
            Database type string or None if not set
        """
        return cls._db_type

    @classmethod
    async def close(cls) -> None:
        """Close the database connection."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
            cls._db_type = None
            logging.info("Database instance closed and cleaned up")

    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if a database instance has been initialized.
        
        Returns:
            True if database is initialized, False otherwise
        """
        return cls._instance is not None

    # Convenience methods that delegate to the current instance
    # These maintain backward compatibility with the old Database class API
    
    @classmethod
    def get_id_field(cls) -> str:
        """Get the database-specific ID field name"""
        return cls.get_instance().id_field

    @classmethod
    def _normalize_document(cls, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database-specific types to application types"""
        if not doc:
            return doc
            
        normalized = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                normalized[key] = str(value)
            else:
                normalized[key] = value
        return normalized

    @classmethod
    async def get_all(cls, collection: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Get all documents from a collection"""
        data, warnings = await cls.get_instance().get_all(collection, unique_constraints)
        
        # Normalize database-specific types
        normalized_data = [cls._normalize_document(doc) for doc in data]
        
        # Convert database warnings to notifications
        for warning in warnings:
            notify_warning(warning, NotificationType.DATABASE, entity=collection, operation="get_all")
            
        return normalized_data, warnings

    @classmethod
    async def get_by_id(cls, collection: str, doc_id: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Get document by ID"""
        data, warnings = await cls.get_instance().get_by_id(collection, doc_id, unique_constraints)
        
        # Normalize database-specific types
        normalized_data = cls._normalize_document(data) if data else data
        
        # Convert database warnings to notifications
        for warning in warnings:
            notify_warning(warning, NotificationType.DATABASE, entity=collection, operation="get_by_id")
            
        return normalized_data, warnings

    @classmethod
    async def save_document(cls, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Save document to collection"""
        data_result, warnings = await cls.get_instance().save_document(collection, data, unique_constraints)
        
        # Convert database warnings to notifications
        for warning in warnings:
            notify_warning(warning, NotificationType.DATABASE, entity=collection, operation="save_document")
            
        return data_result, warnings

    @classmethod
    async def delete_document(cls, collection: str, doc_id: str) -> bool:
        """Delete document from collection"""
        return await cls.get_instance().delete_document(collection, doc_id)

