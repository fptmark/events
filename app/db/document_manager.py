"""
Document CRUD operations with explicit parameters.
No dependency on RequestContext - can be used standalone.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

from app.services.notification import validation_warning, not_found_warning
from app.db.core_manager import CoreManager


class DocumentManager(ABC):
    """Document CRUD operations with clean, focused interface"""
    
    @abstractmethod
    async def get_all(
        self, 
        entity_type: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of documents with explicit parameters.
        
        Args:
            entity_type: Entity type (e.g., "user", "account")
            sort: List of (field, direction) tuples, e.g., [("firstName", "asc")]
            filter: Filter conditions, e.g., {"status": "active", "age": {"$gte": 21}}
            page: Page number (1-based)
            pageSize: Number of items per page
            
        Returns:
            Tuple of (documents, total_count)
        """
        pass
    
    @abstractmethod
    async def get(
        self,
        id: str,
        entity_type: str,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get single document by ID.
        
        Args:
            id: Document ID
            entity_type: Entity type (e.g., "user", "account") 
            
        Returns:
            Tuple of (document, count) where count is 1 if found, 0 if not found
        """
        pass
    
    async def create(
        self,
        entity_type: str,
        data: Dict[str, Any],
        validate: bool = True
    ) -> Tuple[Dict[str, Any], int]:
        """
        Create new document. If data contains 'id', use it as _id, otherwise auto-generate.
        
        Args:
            entity_type: Entity type (e.g., "user", "account")
            data: Document data to save
            validate: Unused parameter (validation handled at model layer)
            
        Returns:
            Tuple of (saved_document, count) where count is 1 if created, 0 if failed
        """
        try:
            # Prepare data for database storage (database-specific)
            prepared_data = self._prepare_datetime_fields(entity_type, data)
            
            # Create in database (database-specific implementation)
            doc = await self._create_document(entity_type, prepared_data)
            
            # Normalize response (remove database-specific ID fields, add standard "id")
            # Should not need this.  public I/F may only use doc['id']
            # saved_doc = self._normalize_document(doc)
            
            return doc, 1
            
        except Exception as e:
            # Convert database errors to notifications instead of raising
            from app.errors import DuplicateConstraintError
            from app.services.notification import system_error, duplicate_warning
            
            if isinstance(e, DuplicateConstraintError):
                duplicate_warning(e.message, entity=e.entity, field=e.field, entity_id=e.entity_id)
            else:
                system_error(f"Create operation failed: {str(e)}")
            return {}, 0

    async def update(
        self,
        entity_type: str,
        data: Dict[str, Any],
        validate: bool = True
    ) -> Tuple[Dict[str, Any], int]:
        """
        Update existing document by id. Fails if document doesn't exist.
        
        Args:
            entity_type: Entity type (e.g., "user", "account")
            data: Document data to update (must contain 'id' field)
            validate: Unused parameter (validation handled at model layer)
            
        Returns:
            Tuple of (saved_document, count) where count is 1 if updated, 0 if failed
        """
        try:
            # ID validation - must exist for update
            if 'id' not in data or not data['id']:
                validation_warning(message="Missing 'id' field or value for update operation", 
                                   entity=entity_type)
                return {}, 0     
            
            # Validate document exists for update
            exists_success = await self._validate_document_exists_for_update(entity_type, data['id'])
            
            if not exists_success:
                validation_warning(message=f"Document to update not found using id", field="id")
                return {}, 0
            
            # Prepare data for database storage (database-specific)
            prepared_data = self._prepare_datetime_fields(entity_type, data)
            
            # Update in database (database-specific implementation)
            doc = await self._update_document(entity_type, prepared_data)
            
            # Normalize response (remove database-specific ID fields, add standard "id")
            # Should not need this.  public I/F may only use doc['id']
            # saved_doc = self._normalize_document(saved_document_with_native_id)
            
            return doc, 1
            
        except Exception as e:
            # Convert database errors to notifications instead of raising
            from app.errors import DuplicateConstraintError
            from app.services.notification import system_error, duplicate_warning
            
            if isinstance(e, DuplicateConstraintError):
                duplicate_warning(e.message, entity=e.entity, field=e.field, entity_id=e.entity_id)
            else:
                system_error(f"Update operation failed: {str(e)}")
            return {}, 0
    
    @abstractmethod
    async def delete(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """
        Delete document by ID.
        
        Args:
            id: Document ID to delete
            entity_type: Entity type (e.g., "user", "account")
            
        Returns:
            Tuple of (deleted_document, count) where count is 1 if deleted, 0 if not found
        """
        pass
    
    @abstractmethod
    async def _validate_document_exists_for_update(self, entity_type: str, id: str) -> bool:
        """
        Validate that document exists for update operations (database-specific).
        Should add not_found_warning and return False if document doesn't exist.
        
        Returns:
            True if document exists, False if not found (with warning added)
        """
        pass
    
    @abstractmethod  
    async def _create_document(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create document in database. If data contains 'id', use it as _id, otherwise auto-generate.
        
        Args:
            entity_type: Entity type
            data: Prepared data (datetime fields converted)
            
        Returns:
            Saved document with database's native ID field populated
        """
        pass

    @abstractmethod  
    async def _update_document(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing document in database.
        
        Args:
            entity_type: Entity type
            data: Prepared data (datetime fields converted, contains 'id' field)
            
        Returns:
            Updated document with database's native ID field populated
        """
        pass
    
    @abstractmethod  
    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance from the concrete implementation"""
        pass
    
    def _normalize_document(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize document by extracting internal id field and renaming to "id".
        
        Args:
            source: Document with database's native ID field
            
        Returns:
            Document with standardized "id" field and native ID field removed
        """
        core = self._get_core_manager()
        dest: Dict[str, Any] = source.copy()
        dest["id"] = core.get_id(source)
        id_field = core.id_field
        if id_field in dest:
            del dest[id_field]  # Remove native _id field
        return dest

    
    # Abstract methods for database-specific logic
    @abstractmethod
    def _prepare_datetime_fields(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for database storage (database-specific)"""
        pass
        
    @abstractmethod
    async def _validate_unique_constraints(
        self, 
        entity_type: str, 
        data: Dict[str, Any], 
        unique_constraints: List[List[str]], 
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints (database-specific implementation)
        
        Args:
            entity_type: Entity type
            data: Document data to validate
            unique_constraints: List of unique constraint field groups
            exclude_id: ID to exclude from validation (for updates)
        
        Returns:
            True if constraints are valid, False if constraint violations detected
        """
        pass