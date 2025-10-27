"""
PostgreSQL database implementation.
Document-oriented storage using JSONB columns.
"""

from ..base import DatabaseInterface
from .core import PostgreSQLCore
from .documents import PostgreSQLDocuments
from .indexes import PostgreSQLIndexes


class PostgreSQLDatabase(DatabaseInterface):
    """PostgreSQL implementation of DatabaseInterface with JSONB storage"""

    def __init__(self, db_uri: str = 'postgresql://localhost:5432/events', case_sensitive_sorting: bool = True):
        self.db_uri = db_uri
        super().__init__(case_sensitive_sorting)

    def _get_manager_classes(self) -> dict:
        """Return manager classes for PostgreSQL"""
        return {
            'core': PostgreSQLCore,
            'documents': PostgreSQLDocuments,
            'indexes': PostgreSQLIndexes
        }

    async def supports_native_indexes(self) -> bool:
        """PostgreSQL supports native unique indexes"""
        return True

    async def initialize(self):
        """Initialize PostgreSQL database"""
        await self.core.init(self.db_uri)
        self._initialized = True
        self._health_state = "healthy"
