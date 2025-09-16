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


__all__ = ['MongoDatabase']