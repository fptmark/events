"""
Main database interface that composes sub-managers.
Clean separation of concerns with explicit parameters.
"""

from abc import ABC, abstractmethod
from .core_manager import CoreManager
from .document_manager import DocumentManager
from .entity_manager import EntityManager
from .index_manager import IndexManager


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
        
        # Composed managers - implemented by concrete drivers
        self.core: CoreManager = self._create_core_manager()
        self.documents: DocumentManager = self._create_document_manager()
        self.entities: EntityManager = self._create_entity_manager()  
        self.indexes: IndexManager = self._create_index_manager()
    
    @abstractmethod
    def _create_core_manager(self) -> CoreManager:
        """Create core manager implementation"""
        pass
    
    @abstractmethod
    def _create_document_manager(self) -> DocumentManager:
        """Create document manager implementation"""
        pass
    
    @abstractmethod
    def _create_entity_manager(self) -> EntityManager:
        """Create entity manager implementation"""
        pass
    
    @abstractmethod
    def _create_index_manager(self) -> IndexManager:
        """Create index manager implementation"""
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