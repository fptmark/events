"""
MongoDB core, entity, and index operations implementation.
Contains MongoCore, MongoEntities, and MongoIndexes classes.
"""

import logging
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..core_manager import CoreManager
from ..entity_manager import EntityManager
from ..index_manager import IndexManager
from app.services.notify import Notification, Error


class MongoCore(CoreManager):
    """MongoDB implementation of core operations"""
    
    def __init__(self, parent):
        self.parent = parent
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
    
    @property
    def id_field(self) -> str:
        return "_id"
    
    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize MongoDB connection"""
        if self._client is not None:
            logging.info("MongoDatabase: Already initialized")
            return

        self._client = AsyncIOMotorClient(connection_str)
        self._db = self._client[database_name]
        
        # Test connection
        await self._client.admin.command('ping')
        self.parent._initialized = True
        logging.info(f"MongoDatabase: Connected to {database_name}")
    
    async def close(self) -> None:
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self.parent._initialized = False
            logging.info("MongoDatabase: Connection closed")
    
    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize ID from MongoDB document"""
        if not document:
            return None
            
        id_value = document.get(self.id_field)
        if id_value is None:
            return None
            
        # Convert ObjectId to string
        from bson import ObjectId
        if isinstance(id_value, ObjectId):
            return str(id_value)
        
        return str(id_value) if id_value else None
    
    def get_connection(self) -> AsyncIOMotorDatabase:
        """Get MongoDB database instance"""
        if self._db is None:
            raise RuntimeError("MongoDB not initialized")
        return self._db


class MongoEntities(EntityManager):
    """MongoDB implementation of entity operations"""
    
    def __init__(self, parent):
        self.parent = parent
    
    async def exists(self, entity_type: str) -> bool:
        """Check if collection exists"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        collection_names = await db.list_collection_names()
        return entity_type in collection_names
    
    async def create(self, entity_type: str, unique_constraints: List[List[str]]) -> bool:
        """Create collection with unique indexes"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            for constraint_fields in unique_constraints:
                index_spec = [(field, 1) for field in constraint_fields]
                await db[entity_type].create_index(index_spec, unique=True)
            return True
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB create entity error: {str(e)}")
        return False

    async def delete(self, entity_type: str) -> bool:
        """Drop collection"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            await db[entity_type].drop()
            return True
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB delete entity error: {str(e)}")
        return False
    
    async def get_all(self) -> List[str]:
        """Get all collection names"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        return await db.list_collection_names()


class MongoIndexes(IndexManager):
    """MongoDB implementation of index operations"""
    
    def __init__(self, parent):
        self.parent = parent
    
    async def create(
        self, 
        entity_type: str, 
        fields: List[str],
        unique: bool = False,
        name: Optional[str] = None
    ) -> None:
        """Create index on collection"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            index_spec = [(field, 1) for field in fields]
            kwargs: Dict[str, Any] = {"unique": unique}
            if name:
                kwargs["name"] = name
                
            await db[entity_type].create_index(index_spec, **kwargs)
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB create index error: {str(e)}")
    
    async def get_all(self, entity_type: str) -> List[List[str]]:
        """Get all unique indexes for collection as field lists"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            field_lists = []
            cursor = db[entity_type].list_indexes()
            
            async for index_info in cursor:
                if index_info.get("name") == "_id_":
                    continue
                    
                if not index_info.get("unique", False):
                    continue
                
                fields = []
                for field_spec in index_info.get("key", {}).items():
                    fields.append(field_spec[0])
                
                if fields:
                    field_lists.append(fields)
            
            return field_lists
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB get indexes error: {str(e)}")
        return []
    
    async def delete(self, entity_type: str, fields: List[str]) -> None:
        """Delete index by field names"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            index_spec = [(field, 1) for field in fields]
            await db[entity_type].drop_index(index_spec)
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB delete index error: {str(e)}")