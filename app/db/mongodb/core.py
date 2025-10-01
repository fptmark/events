"""
MongoDB core, entity, and index operations implementation.
Contains MongoCore, MongoEntities, MongoIndexes and MongoDatabase classes.
"""

import logging
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..base import DatabaseInterface
from ..core_manager import CoreManager
from ..entity_manager import EntityManager
from ..index_manager import IndexManager
from app.services.notify import Notification, Error


class MongoCore(CoreManager):
    """MongoDB implementation of core operations"""

    def __init__(self, database):
        super().__init__(database)
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
        self.database._initialized = True
        logging.info(f"MongoDatabase: Connected to {database_name}")
    
    async def close(self) -> None:
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self.database._initialized = False
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

    async def wipe_and_reinit(self) -> bool:
        """Drop all collections and reinitialize (MongoDB doesn't have mapping issues)"""
        db = self._db
        if db is not None:
            try:
                self.database._ensure_initialized()
                # client = self._client

                # Get all collection names
                collection_names = await db.list_collection_names()

                # Drop all collections
                for collection_name in collection_names:
                    await db.drop_collection(collection_name)

                return True

            except Exception as e:
                logging.error(f"MongoDB wipe and reinit failed: {e}")
        return False

    async def get_status_report(self) -> dict:
        """Get MongoDB database status (no mapping validation needed)"""
        self.database._ensure_initialized()
        client = self._client
        db = self._db
        if db is not None and client is not None:
            try:

                # Get server info
                server_info = await client.server_info()

                # Get database stats
                db_stats = await db.command("dbStats")

                # Get collection info
                collection_names = await db.list_collection_names()
                collections_details = {}

                for collection_name in collection_names:
                    try:
                        coll_stats = await db.command("collStats", collection_name)
                        collections_details[collection_name] = {
                            "doc_count": coll_stats.get("count", 0),
                            "storage_size": coll_stats.get("storageSize", 0),
                            "index_count": coll_stats.get("nindexes", 0)
                        }
                    except Exception as e:
                        collections_details[collection_name] = {
                            "error": f"Could not get stats: {str(e)}"
                        }

                # Create standardized entities dict for testing
                entities = {}
                for collection_name, details in collections_details.items():
                    if "error" not in details:
                        # Capitalize collection name to match entity naming convention
                        entity_name = collection_name.capitalize()
                        doc_count = details.get("doc_count", 0)
                        entities[entity_name] = doc_count

                return {
                    "database": "mongodb",
                    "status": "healthy",  # MongoDB doesn't have mapping validation issues
                    "entities": entities,
                    "details": {
                        "server": {
                            "version": server_info.get("version", "unknown"),
                            "host": getattr(client, "address", "unknown")
                        },
                        "db_info": {
                            "name": db.name,
                            "data_size": db_stats.get("dataSize", 0),
                            "storage_size": db_stats.get("storageSize", 0)
                        },
                        "collections": {
                            "total": len(collection_names),
                            "details": collections_details
                        }
                    }
                }

            except Exception as e:
                return {
                    "database": "mongodb",
                    "status": "error",
                    "entities": {},
                    "error": str(e)
                }
        return {}

class MongoEntities(EntityManager):
    """MongoDB implementation of entity operations"""

    def __init__(self, database):
        super().__init__(database)
    
    async def exists(self, entity_type: str) -> bool:
        """Check if collection exists"""
        self.database._ensure_initialized()
        db = self.database.core.get_connection()
        
        collection_names = await db.list_collection_names()
        return entity_type in collection_names
    
    async def create(self, entity_type: str, unique_constraints: List[List[str]]) -> bool:
        """Create collection with unique indexes"""
        self.database._ensure_initialized()
        db = self.database.core.get_connection()
        
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
        self.database._ensure_initialized()
        db = self.database.core.get_connection()
        
        try:
            await db[entity_type].drop()
            return True
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB delete entity error: {str(e)}")
        return False
    
    async def get_all(self) -> List[str]:
        """Get all collection names"""
        self.database._ensure_initialized()
        db = self.database.core.get_connection()
        
        return await db.list_collection_names()


class MongoIndexes(IndexManager):
    """MongoDB implementation of index operations"""

    def __init__(self, database):
        super().__init__(database)
    
    async def create(
        self, 
        entity_type: str, 
        fields: List[str],
        unique: bool = False,
        name: Optional[str] = None
    ) -> None:
        """Create index on collection"""
        self.database._ensure_initialized()
        db = self.database.core.get_connection()
        
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
        self.database._ensure_initialized()
        db = self.database.core.get_connection()
        
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
        self.database._ensure_initialized()
        db = self.database.core.get_connection()
        
        try:
            index_spec = [(field, 1) for field in fields]
            await db[entity_type].drop_index(index_spec)
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB delete index error: {str(e)}")


class MongoDatabase(DatabaseInterface):
    """MongoDB implementation of DatabaseInterface"""

    def _get_manager_classes(self) -> dict:
        """Return MongoDB manager classes"""
        from .documents import MongoDocuments

        return {
            'core': MongoCore,
            'documents': MongoDocuments,
            'entities': MongoEntities,
            'indexes': MongoIndexes
        }

    def supports_native_indexes(self) -> bool:
        """MongoDB supports native unique indexes"""
        return True
