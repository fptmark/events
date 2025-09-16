"""
Elasticsearch database driver implementation.
"""

from ..base import DatabaseInterface
from .core import ElasticsearchCore, ElasticsearchEntities, ElasticsearchIndexes
from .documents import ElasticsearchDocuments


class ElasticsearchDatabase(DatabaseInterface):
    """Elasticsearch implementation of DatabaseInterface"""
    
    def _get_manager_classes(self) -> dict:
        """Return Elasticsearch manager classes"""
        return {
            'core': ElasticsearchCore,
            'documents': ElasticsearchDocuments,
            'entities': ElasticsearchEntities,
            'indexes': ElasticsearchIndexes
        }
    
    async def supports_native_indexes(self) -> bool:
        """Elasticsearch does not support native unique indexes"""
        return False


__all__ = ['ElasticsearchDatabase']