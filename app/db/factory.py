from typing import Optional
import logging

from .base import DatabaseInterface
from .elasticsearch import ElasticsearchDatabase


class DatabaseFactory:
    """
    Factory class for creating and managing database instances.
    
    Supports runtime selection of database backends and maintains
    a singleton instance for the application.
    """
    
    _instance: Optional[DatabaseInterface] = None
    _db_type: Optional[str] = None

    @classmethod
    def create(cls, db_type: str) -> DatabaseInterface:
        """
        Create a database instance for the specified type.
        
        Args:
            db_type: Database type ('elasticsearch', 'mongodb', etc.)
            
        Returns:
            DatabaseInterface implementation
            
        Raises:
            ValueError: If database type is not supported
        """
        if db_type == "elasticsearch":
            return ElasticsearchDatabase()
        elif db_type == "mongodb":
            # Import here to avoid circular dependencies and optional dependency
            try:
                from .mongodb import MongoDatabase
                return MongoDatabase()
            except ImportError:
                raise ValueError(
                    f"MongoDB support not available. Install required dependencies for MongoDB."
                )
        else:
            supported_types = ["elasticsearch", "mongodb"]
            raise ValueError(
                f"Unknown database type: {db_type}. "
                f"Supported types: {', '.join(supported_types)}"
            )

    @classmethod
    def get_instance(cls) -> DatabaseInterface:
        """
        Get the current database instance.
        
        Returns:
            DatabaseInterface: Current database instance
            
        Raises:
            RuntimeError: If no database instance has been set
        """
        if cls._instance is None:
            raise RuntimeError(
                "Database not initialized. Call DatabaseFactory.set_instance() first."
            )
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
        """
        Close the current database instance and cleanup.
        
        Should be called during application shutdown.
        """
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
    async def find_all(cls, collection: str, model_cls):
        """Find all documents in collection"""
        return await cls.get_instance().find_all(collection, model_cls)

    @classmethod
    async def get_by_id(cls, collection: str, doc_id: str, model_cls):
        """Get document by ID"""
        return await cls.get_instance().get_by_id(collection, doc_id, model_cls)

    @classmethod
    async def save_document(cls, collection: str, doc_id, data, unique_constraints=None):
        """Save document to collection"""
        return await cls.get_instance().save_document(collection, doc_id, data, unique_constraints)

    @classmethod
    async def delete_document(cls, collection: str, doc_id: str) -> bool:
        """Delete document from collection"""
        return await cls.get_instance().delete_document(collection, doc_id)

    @classmethod
    async def check_unique_constraints(cls, collection: str, constraints, 
                                     data, exclude_id=None):
        """Check uniqueness constraints"""
        return await cls.get_instance().check_unique_constraints(
            collection, constraints, data, exclude_id
        )

    @classmethod
    async def exists(cls, collection: str, doc_id: str) -> bool:
        """Check if document exists"""
        return await cls.get_instance().exists(collection, doc_id)

    @classmethod
    def validate_document(cls, doc_data, model_cls):
        """Validate document data against model"""
        return cls.get_instance().validate_document(doc_data, model_cls)