"""
MongoDB database driver implementation.
"""

from ..base import DatabaseInterface
from .core import MongoCore, MongoEntities, MongoIndexes
from .documents import MongoDocuments


class MongoDatabase(DatabaseInterface):
    """MongoDB implementation of DatabaseInterface"""
    
    def _get_manager_classes(self) -> dict:
        """Return MongoDB manager classes"""
        return {
            'core': MongoCore,
            'documents': MongoDocuments,
            'entities': MongoEntities,
            'indexes': MongoIndexes
        }
    
    async def supports_native_indexes(self) -> bool:
        """MongoDB supports native unique indexes"""
        return True

    async def wipe_and_reinit(self) -> bool:
        """Drop all collections and reinitialize (MongoDB doesn't have mapping issues)"""
        try:
            self._ensure_initialized()
            mongo_core = self.core
            client = mongo_core.get_connection()
            db = mongo_core._db

            # Get all collection names
            collection_names = await db.list_collection_names()

            # Drop all collections
            for collection_name in collection_names:
                await db.drop_collection(collection_name)

            return True

        except Exception as e:
            import logging
            logging.error(f"MongoDB wipe and reinit failed: {e}")
            return False

    async def get_status_report(self) -> dict:
        """Get MongoDB database status (no mapping validation needed)"""
        try:
            self._ensure_initialized()
            mongo_core = self.core
            client = mongo_core._client
            db = mongo_core._db

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

            return {
                "database": "mongodb",
                "server": {
                    "version": server_info.get("version", "unknown"),
                    "host": getattr(client, "address", "unknown")
                },
                "db_info": {
                    "name": mongo_core._db.name,
                    "data_size": db_stats.get("dataSize", 0),
                    "storage_size": db_stats.get("storageSize", 0)
                },
                "collections": {
                    "total": len(collection_names),
                    "details": collections_details
                },
                "status": "healthy"  # MongoDB doesn't have mapping validation issues
            }

        except Exception as e:
            return {
                "database": "mongodb",
                "status": "error",
                "error": str(e)
            }


__all__ = ['MongoDatabase']