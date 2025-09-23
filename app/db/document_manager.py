"""
Document CRUD operations with explicit parameters.
No dependency on RequestContext - can be used standalone.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

from app.services.notify import Notification, Warning, Error
from app.db.core_manager import CoreManager
from app.services.metadata import MetadataService


class DocumentManager(ABC):
    """Document CRUD operations with clean, focused interface"""
    
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
        # Convert names to proper case if database is case-sensitive
        if self.isInternallyCaseSensitive():
            entity_type = MetadataService.get_proper_name(entity_type)
            sort = self._get_proper_sort_fields(sort, entity_type)
            filter = self._get_proper_filter_fields(filter, entity_type)

        docs, count = await self._get_all_impl(entity_type, sort, filter, page, pageSize)
        for i in range(0, len(docs) - 1):
            docs[i] = self._remove_sub_objects(entity_type, docs[i])    # ignore sub-objs in the db (should not be there anyway)
        return docs, count

    @abstractmethod
    async def _get_all_impl(
        self,
        entity_type: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Database-specific implementation of get_all"""
        pass
    
    async def get(
        self,
        entity_type: str,
        id: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get single document by ID.

        Args:
            id: Document ID
            entity_type: Entity type (e.g., "user", "account")
            viewspec: View specification for field selection

        Returns:
            Tuple of (document, count) where count is 1 if found, 0 if not found
        """
        # Convert names to proper case if database is case-sensitive
        if self.isInternallyCaseSensitive():
            entity_type = MetadataService.get_proper_name(entity_type)

        doc, count = await self._get_impl(id, entity_type)
        return self._remove_sub_objects(entity_type, doc), count # remove sub-objects in the db (should not be there anyway)

    @abstractmethod
    async def _get_impl(
        self,
        id: str,
        entity_type: str
    ) -> Tuple[Dict[str, Any], int]:
        """Database-specific implementation of get"""
        pass
    
    async def create(
        self,
        entity_type: str,
        data: Dict[str, Any],
        validate: bool = True       # False for testing purposes.  is this where the validation should run???
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
        # Convert entity name to proper case if database is case-sensitive
        if self.isInternallyCaseSensitive():
            entity_type = MetadataService.get_proper_name(entity_type)

        # Prepare data for database storage (database-specific)
        prepared_data = self._prepare_datetime_fields(entity_type, data)

        # Remove any sub-objects so we don't store them in the db
        prepared_data = self._remove_sub_objects(entity_type, prepared_data)

        # Create in database (database-specific implementation)
        doc = await self._create_impl(entity_type, prepared_data)

        return doc, 1
        
    @abstractmethod  
    async def _create_impl(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

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
        # Convert entity name to proper case if database is case-sensitive
        if self.isInternallyCaseSensitive():
            entity_type = MetadataService.get_proper_name(entity_type)

        # ID validation - must exist for update
        if 'id' not in data or not data['id']:
            Notification.error(Error.REQUEST, "Missing 'id' field or value for update operation")

        # Validate document exists for update
        exists_success = await self._validate_document_exists_for_update(entity_type, data['id']) if validate else True

        if not exists_success:
            Notification.error(Error.REQUEST, "Document to update not found using id")

        # Prepare data for database storage (database-specific)
        prepared_data = self._prepare_datetime_fields(entity_type, data)

        # Remove any sub-objects so we don't store them in the db
        prepared_data = self._remove_sub_objects(entity_type, prepared_data)

        # Update in database (database-specific implementation)
        doc = await self._update_impl(entity_type, prepared_data)

        return doc, 1
            
    @abstractmethod  
    async def _update_impl(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    async def delete(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """
        Delete document by ID.

        Args:
            id: Document ID to delete
            entity_type: Entity type (e.g., "user", "account")

        Returns:
            Tuple of (deleted_document, count) where count is 1 if deleted, 0 if not found
        """
        # Convert entity name to proper case if database is case-sensitive
        if self.isInternallyCaseSensitive():
            entity_type = MetadataService.get_proper_name(entity_type)

        return await self._delete_impl(id, entity_type)

    @abstractmethod
    async def _delete_impl(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """Database-specific implementation of delete"""
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
    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance from the concrete implementation"""
        pass

    @abstractmethod
    def isInternallyCaseSensitive(self) -> bool:
        """
        Return True if the database is internally case-sensitive for field names.
        If True, the base class will convert entity and field names to proper case.
        If False, names will be passed to the driver as-is.
        """
        pass
    
    def _normalize_document(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize document by extracting internal id field and renaming to "id".
        
        Args:
            source: Document with database's native ID field
            
        Returns:
            Document with standardized "id" field first, then other fields
        """
        core = self._get_core_manager()
        id_field = core.id_field
        
        # Create new dict with 'id' first
        dest: Dict[str, Any] = {"id": core.get_id(source)}
        
        # Add all other fields except the native ID field
        for key, value in source.items():
            if key != id_field:
                dest[key] = value
                
        return dest

    def _get_proper_sort_fields(self, sort_fields: Optional[List[Tuple[str, str]]], entity_type: str) -> Optional[List[Tuple[str, str]]]:
        """Get sort fields with proper case names if database is case-sensitive"""
        if not sort_fields or not self.isInternallyCaseSensitive():
            return sort_fields

        proper_sort = []
        for field_name, direction in sort_fields:
            proper_field_name = MetadataService.get_proper_name(entity_type, field_name)
            proper_sort.append((proper_field_name, direction))
        return proper_sort

    def _get_proper_filter_fields(self, filters: Optional[Dict[str, Any]], entity_type: str) -> Optional[Dict[str, Any]]:
        """Get filter dict with proper case field names if database is case-sensitive"""
        if not filters or not self.isInternallyCaseSensitive():
            return filters

        proper_filters = {}
        for field_name, value in filters.items():
            proper_field_name = MetadataService.get_proper_name(entity_type, field_name)
            # Value is preserved as-is (operators like $gte, $lt, etc. are MongoDB-specific, not field names)
            proper_filters[proper_field_name] = value
        return proper_filters

    def _get_proper_view_fields(self, view_spec: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Get view spec with proper case field names if database is case-sensitive"""
        if not view_spec or not self.isInternallyCaseSensitive():
            return view_spec

        proper_view_spec = {}
        for fk_entity_name, field_list in view_spec.items():
            # Convert the foreign entity name to proper case
            proper_fk_entity_name = MetadataService.get_proper_name(fk_entity_name)

            # Convert each field name in the field list to proper case
            proper_field_list = []
            for field_name in field_list:
                proper_field_name = MetadataService.get_proper_name(fk_entity_name, field_name)
                proper_field_list.append(proper_field_name)

            proper_view_spec[proper_fk_entity_name] = proper_field_list

        return proper_view_spec


    # Abstract methods for database-specific logic
    @abstractmethod
    def _prepare_datetime_fields(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for database storage (database-specific)"""
        pass
    
    @abstractmethod
    def _convert_filter_values(self, filters: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Convert filter values to database-appropriate types (database-specific)"""
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

    def _remove_sub_objects(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any sub-objects from the data before storing in the database"""
        # look for any <field>id that are ObjectId types and remove the corresponding <field> sub-object
        cleaned_data = data.copy()
        for field in data:
            if MetadataService.get(entity_type, field + "id", 'type') == 'ObjectId':
                cleaned_data.pop(field)

        return cleaned_data