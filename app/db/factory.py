"""
Database factory for the new refactored architecture.
Creates and manages database instances with clean manager separation.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple

from app.services.notify import Notification, Error

from .base import DatabaseInterface
from .mongodb import MongoDatabase
from .elasticsearch import ElasticsearchDatabase


class DatabaseFactory:
    """
    Factory for creating and managing database instances.
    
    Usage:
        # Initialize
        db = await DatabaseFactory.initialize("mongodb", connection_str, db_name)
        
        # Use managers
        users = await db.documents.get_all("user", page=1, pageSize=10)
        user = await db.documents.get("123", "user")
        await db.documents.create("user", user_data)
        
        # Admin operations
        await db.entities.create("user", [["email"], ["username"]])
        await db.indexes.create("user", ["email"], unique=True)
    """
    
    _instance: Optional[DatabaseInterface] = None
    _db_type: Optional[str] = None

    @classmethod
    async def initialize(
        cls, 
        db_type: str, 
        connection_str: str, 
        database_name: str, 
        case_sensitive_sorting: bool = False
    ) -> DatabaseInterface:
        """
        Initialize database connection with new architecture.
        
        Args:
            db_type: Database type ("mongodb" or "elasticsearch")
            connection_str: Database connection string
            database_name: Database name
            case_sensitive_sorting: Whether to use case-sensitive sorting
            
        Returns:
            DatabaseInterface instance with composed managers
        """
        if cls._instance is not None:
            logging.info("DatabaseFactory: Already initialized")
            return cls._instance
            
        try:
            # Create database instance
            db: DatabaseInterface
            if db_type.lower() == "mongodb":
                db = MongoDatabase(case_sensitive_sorting=case_sensitive_sorting)
            elif db_type.lower() == "elasticsearch":
                db = ElasticsearchDatabase(case_sensitive_sorting=case_sensitive_sorting) 
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
                
            # Initialize connection
            await db.core.init(connection_str, database_name)
            
            cls._instance = db
            cls._db_type = db_type
            
            logging.info(f"DatabaseFactory: Initialized {db_type} database")
            
        except Exception as e:
            from app.services.notify import Notification, Error
            Notification.error(Error.DATABASE, f"Failed to initialize database: {str(e)}")

        return db

    @classmethod
    def get_instance(cls) -> DatabaseInterface:
        """Get the current database instance"""
        if cls._instance is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def set_instance(cls, instance: DatabaseInterface, db_type: str) -> None:
        """
        Set the current database instance (mainly for testing).
        
        Args:
            instance: Database instance to set
            db_type: Database type for logging
        """
        cls._instance = instance
        cls._db_type = db_type
        logging.info(f"Database instance set to: {db_type}")

    @classmethod
    def get_db_type(cls) -> Optional[str]:
        """Get the currently configured database type"""
        return cls._db_type

    @classmethod
    async def close(cls) -> None:
        """Close the database connection and clean up"""
        if cls._instance is not None:
            await cls._instance.core.close()
            cls._instance = None
            cls._db_type = None
            logging.info("Database instance closed and cleaned up")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if a database instance has been initialized"""
        return cls._instance is not None

    
    @classmethod
    async def get_all(cls, entity_type: str, 
                      sort: Optional[List[Tuple[str, str]]] = None, filter: Optional[Dict[str, Any]] = None, 
                      page: int=1, pageSize: int=25, view_spec: Dict[str, Any] = {}) -> tuple[List[Dict[str, Any]], int]:

        db = cls.get_instance()
        documents, total_count = await db.documents.get_all(
            entity_type=entity_type,
            sort=sort,
            filter=filter,
            page=page,
            pageSize=pageSize,
            view_spec=view_spec
        )

        return documents, total_count

    @classmethod
    async def get(cls, entity_type: str, doc_id: str, view_spec: Dict[str, Any] = {}) -> Tuple[Dict[str, Any], int]:
        """Get document by ID. Returns (document, count)."""
        db = cls.get_instance()
        document, count = await db.documents.get(
            entity_type=entity_type,
            id=doc_id,
            view_spec=view_spec
        )

        return document, count

    @classmethod
    async def create(cls, entity_type: str, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """Create document. Returns (document, count)."""
        db = cls.get_instance()
        document, count = await db.documents.create(
            entity_type=entity_type,
            data=data,
        )
        
        return document, count

    @classmethod
    async def update(cls, entity_type: str, data: Dict[str, Any], validate: bool = True) -> Tuple[Dict[str, Any], int]:
        """Update document. Returns (document, count)."""
        id = (data.pop('id', '') or '').strip()
        if id:
            data['id'] = id
        else:
            Notification.error(stop_type=Error.REQUEST, message=f"Missing or empty 'id' field = ({id}) for update operation", entity_type=entity_type, field="id")
            return {}, 0

        db = cls.get_instance()
        document, count = await db.documents.update(
            entity_type=entity_type,
            data=data,
            validate=validate
        )
        
        return document, count

    @classmethod
    async def delete(cls, entity_type: str, doc_id: str) -> Tuple[Dict[str, Any], int]:
        """Delete document. Returns (deleted_document, count)."""
        db = cls.get_instance()
        deleted_document, count = await db.documents.delete(
            id=doc_id,
            entity_type=entity_type
        )
        
        return deleted_document, count

    @classmethod
    async def remove_entity(cls, entity_type: str) -> bool:
        """Remove entire entity collection/index"""
        db = cls.get_instance()
        return await db.entities.delete(entity_type)