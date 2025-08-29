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
    ) -> Tuple[List[Dict[str, Any]], bool, int]:
        """
        Get paginated list of documents with explicit parameters.
        
        Args:
            entity_type: Entity type (e.g., "user", "account")
            sort: List of (field, direction) tuples, e.g., [("firstName", "asc")]
            filter: Filter conditions, e.g., {"status": "active", "age": {"$gte": 21}}
            page: Page number (1-based)
            pageSize: Number of items per page
            
        Returns:
            Tuple of (documents, success, total_count)
        """
        pass
    
    @abstractmethod
    async def get(
        self,
        id: str,
        entity_type: str,
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Get single document by ID.
        
        Args:
            id: Document ID
            entity_type: Entity type (e.g., "user", "account") 
            view_spec: View specification for FK expansion (passed to model layer)
            
        Returns:
            Tuple of (document, success)
        """
        pass
    
    async def save(
        self,
        entity_type: str,
        data: Dict[str, Any],
        id: str = '',
        validate: bool = True
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Base class save implementation - handles validation and delegates storage to database-specific method.
        
        Args:
            entity_type: Entity type (e.g., "user", "account")
            data: Document data to save (any 'id' field will be ignored/removed)
            id: Document ID for updates (empty = create new document)
            validate: Whether to validate data and constraints (False for testing)
            
        Returns:
            Tuple of (saved_document, success)
        """
        try:
            # Clean data - remove any id field, only use id parameter
            clean_data = data.copy()
            if 'id' in clean_data:
                del clean_data['id']
            
            # 1. Validate field types and constraints - collect all warnings first
            if validate:
                validation_success = self._validate_field_types(entity_type, clean_data)    # adds warnings automatically

            # 2. For updates, validate document exists (database-specific)
            if id.strip():
                exists_success = await self._validate_document_exists_for_update(entity_type, id)
                
            # 3. Get unique constraints from metadata and validate
            from app.services.metadata import MetadataService
            metadata = MetadataService.get(entity_type)
            unique_constraints = metadata.get('uniques', []) if metadata else []
            if unique_constraints:
                constraint_success = await self._validate_unique_constraints(entity_type, clean_data, unique_constraints, id if id.strip() else None)
            
            # If validation failed, return empty result with False
            if not (validation_success and exists_success and constraint_success):
                return {}, False
            
            # 4. Prepare data for database storage (database-specific)
            prepared_data = self._prepare_datetime_fields(entity_type, clean_data)
            
            # 5. Save to database (database-specific implementation)
            saved_document_with_native_id = await self._save_to_database(entity_type, prepared_data, id)
            
            # 6. Normalize response (remove database-specific ID fields, add standard "id")
            saved_doc = self._normalize_document(saved_document_with_native_id)
            
            return saved_doc, True
            
        except Exception as e:
            # Let database-specific errors bubble up
            raise
    
    @abstractmethod
    async def delete(self, id: str, entity_type: str) -> bool:
        """
        Delete document by ID.
        
        Args:
            id: Document ID to delete
            entity_type: Entity type (e.g., "user", "account")
            
        Returns:
            True if deleted successfully
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
    async def _save_to_database(self, entity_type: str, data: Dict[str, Any], id: str) -> Dict[str, Any]:
        """
        Save document to database (database-specific implementation).
        
        Args:
            entity_type: Entity type
            data: Prepared data (datetime fields converted, no "id" field)
            id: Document ID for updates (empty string = create new)
            
        Returns:
            Saved document with database's native ID field populated
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

    # Shared validation methods for save operations
    def _validate_field_types(self, entity_type: str, data: Dict[str, Any]) -> bool:
        """Validate business logic field constraints using metadata
        
        Returns:
            True if validation passed, False if validation warnings were generated
        """
        from app.services.metadata import MetadataService
        from app.services.notification import validation_warning
        
        metadata = MetadataService.get(entity_type)
        if not metadata:
            validation_warning(f"Unknown entity type: {entity_type}", entity=entity_type)
            return False
            
        fields_meta = metadata.get('fields', {})
        validation_success = True
        
        for field_name, value in data.items():
            if field_name not in fields_meta:
                continue  # Skip unknown fields 
                
            field_meta = fields_meta[field_name]
            
            # Required field check
            if field_meta.get('required') and not value:
                validation_warning(f"Required field '{field_name}' is missing or empty", entity=entity_type, field=field_name)
                validation_success = False
                
            if value is None:
                continue  # Skip null values for other validations
                
            # String length validation
            if field_meta.get('type') == 'String' and isinstance(value, str):
                min_len = field_meta.get('min_length')
                max_len = field_meta.get('max_length')
                if min_len and len(value) < min_len:
                    validation_warning(f"Field '{field_name}' is too short (minimum {min_len} characters)", entity=entity_type, field=field_name)
                    validation_success = False
                if max_len and len(value) > max_len:
                    validation_warning(f"Field '{field_name}' is too long (maximum {max_len} characters)", entity=entity_type, field=field_name)
                    validation_success = False
            
            # Enum validation
            if 'enum' in field_meta:
                valid_values = field_meta['enum'].get('values', [])
                if value not in valid_values:
                    validation_warning(f"Invalid value '{value}' for field '{field_name}'. Valid values: {valid_values}", entity=entity_type, field=field_name)
                    validation_success = False
                    
            # Numeric range validation  
            if field_meta.get('type') in ['Integer', 'Float', 'Currency'] and isinstance(value, (int, float)):
                if 'ge' in field_meta and value < field_meta['ge']:
                    validation_warning(f"Field '{field_name}' value {value} is below minimum {field_meta['ge']}", entity=entity_type, field=field_name)
                    validation_success = False
                if 'le' in field_meta and value > field_meta['le']:
                    validation_warning(f"Field '{field_name}' value {value} is above maximum {field_meta['le']}", entity=entity_type, field=field_name)
                    validation_success = False
        
        return validation_success
    
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
        
        Returns:
            True if constraints are valid, False if constraint violations detected
        """
        pass