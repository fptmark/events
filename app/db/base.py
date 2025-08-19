from abc import ABC, abstractmethod
from typing import Any, Dict, List, TypeVar, Type, Optional, Tuple, Callable
from pydantic import BaseModel
from functools import wraps
import hashlib
from ..errors import DatabaseError

T = TypeVar('T', bound=BaseModel)

class SyntheticDuplicateError(Exception):
    """Raised when synthetic index detects duplicate"""
    def __init__(self, collection: str, field: str, value: Any):
        self.collection = collection
        self.field = field
        self.value = value
        super().__init__(f"Synthetic duplicate constraint violation: {field} = {value} in {collection}")

class DatabaseInterface(ABC):
    """Base interface for database implementations"""
    
    def __init__(self, case_sensitive_sorting: bool = False):
        self._initialized = False
        self.case_sensitive_sorting = case_sensitive_sorting  # Default to case-insensitive sorting
    
    def _ensure_initialized(self) -> None:
        """Ensure database is initialized, raise RuntimeError if not"""
        if not self._initialized:
            raise RuntimeError(f"{self.__class__.__name__} not initialized")
    
    def _handle_connection_error(self, error: Exception, database_name: str) -> None:
        """Handle connection errors with standardized DatabaseError"""
        raise DatabaseError(
            message=f"Failed to connect to {self.__class__.__name__}: {str(error)}",
            entity="connection", 
            operation="init"
        )
    
    def _normalize_id(self, doc_id: str) -> str:
        """Normalize document ID to lowercase for consistent cross-database behavior"""
        if not doc_id:
            return doc_id
        return str(doc_id).lower()
    
    def _normalize_date_string(self, date_str: str) -> str:
        """Normalize date string to ISO format for consistent date comparison across databases."""
        if not isinstance(date_str, str):
            return date_str
        
        date_str = date_str.strip()
        
        # If already has time component, return as-is
        if 'T' in date_str or ' ' in date_str:
            return date_str
            
        # If just date (YYYY-MM-DD), add time component for consistency
        if len(date_str) == 10 and date_str.count('-') == 2:
            return f"{date_str}T00:00:00"
            
        return date_str
    
    def _convert_to_date_object(self, date_value: Any) -> Any:
        """Convert ISO date string to native date object for database operations."""
        from datetime import datetime
        
        if not isinstance(date_value, str):
            return date_value
        
        try:
            # First normalize the date string format
            normalized_str = self._normalize_date_string(date_value)
            
            # Convert to datetime object for native date comparisons
            return datetime.fromisoformat(normalized_str.replace('Z', '+00:00'))
            
        except (ValueError, AttributeError):
            # If conversion fails, return original value
            return date_value
    
    def _wrap_database_operation(self, operation: str, entity: str):
        """Decorator to wrap database operations with error handling"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except DatabaseError:
                    # Re-raise existing DatabaseError with context preserved
                    raise
                except Exception as e:
                    raise DatabaseError(
                        message=str(e),
                        entity=entity,
                        operation=operation
                    )
            return wrapper
        return decorator
    
    def _validate_list_params(self, list_params):
        """Validate and sanitize list_params to prevent None errors"""
        if not list_params:
            return list_params
            
        # Ensure filters is never None
        if list_params.filters is None:
            list_params.filters = {}
            
        # Ensure sort_fields is never None
        if list_params.sort_fields is None:
            list_params.sort_fields = []
            
        return list_params
    
    def _validate_document_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize document data to prevent None errors"""
        if data is None:
            return {}
        if not isinstance(data, dict):
            return {}
        return data
    
    @property
    @abstractmethod
    def id_field(self) -> str:
        """Get the ID field name for this database"""
        pass

    @abstractmethod
    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize the ID from a document"""
        pass

    @abstractmethod
    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize the database connection"""
        pass

    @abstractmethod
    async def get_all(self, collection: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Get all documents from a collection with count"""
        pass

    @abstractmethod
    async def _get_list_impl(self, collection: str, unique_constraints: Optional[List[List[str]]] = None, list_params=None, entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Get paginated/filtered list of documents from a collection with count"""
        pass

    @abstractmethod
    def _build_query_filter(self, list_params, entity_metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Build database-specific query filter from ListParams"""
        pass

    @abstractmethod  
    def _build_sort_spec(self, list_params, entity_metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Build database-specific sort specification from ListParams"""
        pass

    @abstractmethod
    async def get_by_id(self, collection: str, doc_id: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Get a document by ID"""
        pass

    @abstractmethod
    async def save_document(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Save a document to the database"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the database connection"""
        pass

    @abstractmethod
    async def collection_exists(self, collection: str) -> bool:
        """Check if a collection exists"""
        pass

    @abstractmethod
    async def create_collection(self, collection: str, indexes: List[Dict[str, Any]]) -> bool:
        """Create a collection with indexes"""
        pass

    @abstractmethod
    async def delete_collection(self, collection: str) -> bool:
        """Delete a collection"""
        pass

    @abstractmethod
    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document"""
        pass

    @abstractmethod
    async def list_collections(self) -> List[str]:
        """List all collections"""
        pass

    @abstractmethod
    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """
        List all indexes for a collection.
        
        Returns:
            List of index dictionaries with standardized format:
            {
                'name': str,           # Index name
                'fields': List[str],   # Field names in the index
                'unique': bool,        # Whether index enforces uniqueness
                'system': bool         # Whether it's a system index (like _id)
            }
        """
        pass

    @abstractmethod
    async def delete_index(self, collection: str, fields: List[str]) -> None:
        """Delete an index from a collection"""
        pass

    @abstractmethod
    async def supports_native_indexes(self) -> bool:
        """Check if database supports native unique indexes"""
        pass
    
    @abstractmethod
    async def document_exists_with_field_value(self, collection: str, field: str, value: Any, exclude_id: Optional[str] = None) -> bool:
        """Check if a document exists with the given field value (excluding optionally specified ID)"""
        pass
    
    # Public wrapper methods with validation
    async def get_list(self, collection: str, unique_constraints: Optional[List[List[str]]] = None, list_params=None, entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Get paginated/filtered list of documents from a collection with count - with parameter validation"""
        # Validate and sanitize list_params
        validated_params = self._validate_list_params(list_params)
        
        # Call the implementation
        return await self._get_list_impl(collection, unique_constraints, validated_params, entity_metadata)
    
    # Optional method for databases that support single field index creation
    async def create_single_field_index(self, collection: str, field: str, index_name: str) -> None:
        """Create a single field index (optional - for synthetic index support)"""
        pass
    
    # Generic synthetic index methods (implemented in base class)
    async def prepare_document_for_save(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Dict[str, Any]:
        """Prepare document for save by adding synthetic hash fields if needed"""
        if not unique_constraints:
            return data
            
        # Check if database supports native indexes
        if await self.supports_native_indexes():
            return data  # Native indexes handle uniqueness
            
        return self._add_synthetic_hash_fields(data, unique_constraints)
    
    async def validate_unique_constraints_before_save(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> None:
        """Validate unique constraints before saving (works for both native and synthetic)"""
        if not unique_constraints:
            return
            
        # Check if database supports native indexes
        if await self.supports_native_indexes():
            return  # Native indexes will handle this during save
            
        # For synthetic indexes, validate manually
        await self._validate_synthetic_constraints(collection, data, unique_constraints)
    
    def _add_synthetic_hash_fields(self, data: Dict[str, Any], unique_constraints: List[List[str]]) -> Dict[str, Any]:
        """Add synthetic hash fields for multi-field unique constraints"""
        result = data.copy()
        
        for constraint_fields in unique_constraints:
            if len(constraint_fields) > 1:
                # Multi-field constraint - add hash field
                hash_field_name = self._get_hash_field_name(constraint_fields)
                values = [str(data.get(field, "")) for field in constraint_fields]
                hash_value = self._generate_constraint_hash(values)
                result[hash_field_name] = hash_value
        
        return result
    
    async def _validate_synthetic_constraints(self, collection: str, data: Dict[str, Any], unique_constraints: List[List[str]]) -> None:
        """Validate synthetic unique constraints"""
        document_id = data.get('id')
        
        for constraint_fields in unique_constraints:
            if len(constraint_fields) == 1:
                # Single field constraint
                field = constraint_fields[0]
                value = data.get(field)
                if value is not None and await self.document_exists_with_field_value(collection, field, value, document_id):
                    raise SyntheticDuplicateError(collection, field, value)
            else:
                # Multi-field constraint - check hash field
                hash_field_name = self._get_hash_field_name(constraint_fields)
                hash_value = data.get(hash_field_name)
                if hash_value and await self.document_exists_with_field_value(collection, hash_field_name, hash_value, document_id):
                    # Create user-friendly error message
                    field_desc = " + ".join(constraint_fields)
                    values = [str(data.get(field, "")) for field in constraint_fields]
                    value_desc = " + ".join(values)
                    raise SyntheticDuplicateError(collection, field_desc, value_desc)
    
    def _get_hash_field_name(self, fields: List[str]) -> str:
        """Generate consistent hash field name for multi-field constraints"""
        return "_".join(sorted(fields)) + "_hash"
    
    def _generate_constraint_hash(self, values: List[str]) -> str:
        """Generate consistent hash for multi-field constraints"""
        combined = "|".join(values)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    # Metadata-driven field type helpers
    def _get_field_name_mapping(self, entity_metadata: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Create cached bidirectional field name mapping (lowercase -> actual, actual -> actual)."""
        if not entity_metadata or 'fields' not in entity_metadata:
            return {}
            
        mapping = {}
        fields = entity_metadata.get('fields', {})
        
        for actual_field_name in fields.keys():
            # Map actual name to itself
            mapping[actual_field_name] = actual_field_name
            # Map lowercase to actual
            lowercase_name = actual_field_name.lower()
            if lowercase_name != actual_field_name:
                mapping[lowercase_name] = actual_field_name
                
        return mapping
    
    def _map_field_name(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> str:
        """Map field name using cached lookup and notify about invalid fields."""
        if not hasattr(self, '_field_mapping_cache'):
            self._field_mapping_cache = {}
        if not hasattr(self, '_notified_invalid_fields'):
            self._notified_invalid_fields = set()
            
        # Use metadata hash as cache key
        cache_key = id(entity_metadata) if entity_metadata else 'none'
        
        if cache_key not in self._field_mapping_cache:
            self._field_mapping_cache[cache_key] = self._get_field_name_mapping(entity_metadata)
            
        mapping = self._field_mapping_cache[cache_key]
        mapped_field = mapping.get(field_name)
        
        # If field not found in mapping and we have metadata, notify about invalid field (only once per field)
        if mapped_field is None and entity_metadata and 'fields' in entity_metadata:
            if field_name not in self._notified_invalid_fields:
                from app.notification import notify_application_error
                notify_application_error(f"Invalid field '{field_name}' does not exist in entity")
                self._notified_invalid_fields.add(field_name)
            
        return mapped_field if mapped_field is not None else field_name
    
    def _get_field_type(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> str:
        """Get field type from entity metadata or default to String."""
        if not entity_metadata:
            return 'String'
        
        # Map lowercase field name to actual metadata field name
        actual_field_name = self._map_field_name(field_name, entity_metadata)
        field_info = entity_metadata.get('fields', {}).get(actual_field_name, {})
        return field_info.get('type', 'String')
    
    def _is_enum_field(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> bool:
        """Check if field has enum values defined in metadata."""
        if not entity_metadata:
            return False
        
        # Map lowercase field name to actual metadata field name
        actual_field_name = self._map_field_name(field_name, entity_metadata)
        field_info = entity_metadata['fields'].get(actual_field_name, {})
        return 'enum' in (field_info or {})
    
    def _is_unique_field(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> bool:
        """Check if field is part of unique constraints in metadata."""
        if not entity_metadata:
            return False
        
        try:
            unique_constraints = entity_metadata.get('uniques', [])
            for constraint in unique_constraints:
                # Ensure constraint is not None and is iterable
                if constraint and hasattr(constraint, '__iter__') and field_name in constraint:
                    return True
        except (AttributeError, TypeError):
            pass  # Ignore metadata parsing errors
        
        return False
    
    def _is_auto_generated_field(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> bool:
        """Check if field is auto-generated from metadata."""
        if not entity_metadata:
            return False
        
        # Map lowercase field name to actual metadata field name
        actual_field_name = self._map_field_name(field_name, entity_metadata)
        field_info = entity_metadata.get('fields', {}).get(actual_field_name, {})
        return field_info.get('autoGenerate', False) or field_info.get('autoUpdate', False)
    
    def _get_default_sort_field(self, entity_metadata: Optional[Dict[str, Any]]) -> str:
        """Get default sort field from metadata - first auto-generated date field or safe fallback."""
        if not entity_metadata:
            return 'createdAt'  # Safe fallback when no metadata
        
        try:
            fields = entity_metadata.get('fields', {})
            
            # Find first auto-generated date/datetime field
            for field_name, field_info in fields.items():
                if (field_info.get('autoGenerate', False) and 
                    field_info.get('type') in ['Date', 'Datetime']):
                    return field_name
        except (AttributeError, TypeError):
            pass  # Ignore metadata parsing errors
        
        # Safe fallback - every entity should have createdAt
        return 'createdAt'
    
    def _needs_keyword_suffix(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> bool:
        """Determine if field needs .keyword suffix for Elasticsearch based on metadata."""
        field_type = self._get_field_type(field_name, entity_metadata)
        
        # These field types don't need .keyword suffix
        if field_type in ['Date', 'Datetime', 'Integer', 'Currency', 'Float', 'Boolean']:
            return False
        
        # Check for id field and ObjectId fields that typically don't need .keyword
        if field_name == 'id' or field_name.endswith('Id'):
            return False
        
        # Check if field is in unique constraints - these are mapped as pure keyword in ES
        if self._is_unique_field(field_name, entity_metadata):
            return False
        
        # String fields with enum should use .keyword for exact matching
        if field_type == 'String' and self._is_enum_field(field_name, entity_metadata):
            return True
        
        # String fields without enum need .keyword for exact operations  
        if field_type == 'String':
            return True
        
        # Default to needing .keyword for unknown types (safer for text fields)
        return True
    
    def _should_use_partial_matching(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> bool:
        """Determine if field should use partial matching for filtering based on metadata."""
        field_type = self._get_field_type(field_name, entity_metadata)
        
        # Only String fields without enum use partial matching
        return field_type == 'String' and not self._is_enum_field(field_name, entity_metadata)

