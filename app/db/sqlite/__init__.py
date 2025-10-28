"""
SQLite database implementation.
Document-oriented storage using JSON columns.
"""

from ..base import DatabaseInterface
from .core import SQLiteCore
from .documents import SqliteDocuments
from .indexes import SqliteIndexes


class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation of DatabaseInterface"""

    def __init__(self, db_path: str = 'events.db', case_sensitive_sorting: bool = False):
        self.db_path = db_path
        super().__init__(case_sensitive_sorting)

    def _get_manager_classes(self) -> dict:
        """Return manager classes for SQLite"""
        return {
            'core': SQLiteCore,
            'documents': SqliteDocuments,
            'indexes': SqliteIndexes
        }

    async def supports_native_indexes(self) -> bool:
        """SQLite supports native unique indexes"""
        return True

    async def initialize(self):
        """Initialize SQLite database"""
        await self.core.init(self.db_path)
        await self.documents.initialize_schema()
        self._initialized = True
        self._health_state = "healthy"
