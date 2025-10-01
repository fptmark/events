"""
Core database operations (connection management, ID handling).
Renamed from DatabaseManager to avoid confusion with main class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union


class CoreManager(ABC):
    """Core database operations - connection and ID management"""

    def __init__(self, database):
        """Initialize with database interface reference"""
        self.database = database
    
    @abstractmethod
    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize database connection"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close database connection"""
        pass
    
    @abstractmethod
    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize document ID"""
        return document.get(self.id_field)

    @property
    @abstractmethod
    def id_field(self) -> str:
        """Get the ID field name for this database"""
        pass

    @abstractmethod
    def get_connection(self) -> Any:
        """Get the database connection/client instance"""
        pass

    def _get_default_sort_field(self, entity_type: str) -> str:
        from app.services.metadata import MetadataService

        fields = MetadataService.fields(entity_type)
        for field_name, field_info in fields.items():
            if field_info.get('autoGenerate', False):
                return field_name
        return self.id_field

    @abstractmethod
    async def wipe_and_reinit(self) -> bool:
        """Wipe all data and reinitialize database with correct structure"""
        pass

    @abstractmethod
    async def get_status_report(self) -> dict:
        """Get comprehensive database status report"""
        pass