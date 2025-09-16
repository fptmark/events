"""
Main database interface that composes sub-managers.
Clean separation of concerns with explicit parameters.
"""

from abc import ABC, abstractmethod
from typing import Type, TYPE_CHECKING
from .core_manager import CoreManager
from .document_manager import DocumentManager
from .entity_manager import EntityManager
from .index_manager import IndexManager

if TYPE_CHECKING:
    pass


class DatabaseInterface(ABC):
    """
    Main database interface that composes specialized managers.
    
    Architecture:
    - core: Connection management, ID handling  
    - documents: CRUD operations
    - entities: Collection management
    - indexes: Index management
    """
    
    def __init__(self, case_sensitive_sorting: bool = False):
        self.case_sensitive_sorting = case_sensitive_sorting
        self._initialized = False
        
        # Get manager classes from concrete implementation
        manager_classes = self._get_manager_classes()
        
        # Create composed managers using template method pattern
        self.core: CoreManager = manager_classes['core'](self)
        self.documents: DocumentManager = manager_classes['documents'](self)
        self.entities: EntityManager = manager_classes['entities'](self)
        self.indexes: IndexManager = manager_classes['indexes'](self)
    
    @abstractmethod
    def _get_manager_classes(self) -> dict:
        """Return dictionary of manager class types for this database"""
        pass
    
    # Utility methods
    def _ensure_initialized(self) -> None:
        """Ensure database is initialized"""
        if not self._initialized:
            raise RuntimeError(f"{self.__class__.__name__} not initialized")
    
    def _normalize_id(self, doc_id: str) -> str:
        """Normalize document ID for consistent cross-database behavior"""
        if not doc_id:
            return doc_id
        return str(doc_id)
    
    # Database-specific methods that drivers might need to implement
    @abstractmethod
    async def supports_native_indexes(self) -> bool:
        """Check if database supports native unique indexes"""
        pass