from abc import ABC, abstractmethod
from typing import Any, Dict, List, TypeVar, Type, Optional, Tuple, Callable
from pydantic import BaseModel
from functools import wraps
import hashlib
from datetime import datetime, timezone
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
    def _build_sort_spec(self, list_params, collection: str, entity_metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Build database-specific sort specification from ListParams"""
        pass

    @abstractmethod
    async def get_by_id(self, collection: str, doc_id: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Get a document by ID"""
        pass

    @abstractmethod
    async def save_document(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None, entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
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
    async def remove_entity(self, collection: str) -> bool:
        """Remove/drop entire entity collection"""
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
    
    # Datetime conversion methods (implemented in base class)
    def _process_datetime_fields_for_save(self, data: Dict[str, Any], entity_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert datetime fields based on metadata before saving to database."""
        if not entity_metadata or 'fields' not in entity_metadata:
            return data
            
        data_copy = data.copy()
        fields_metadata = entity_metadata['fields']
        
        for field_name, field_meta in fields_metadata.items():
            if field_name in data_copy and data_copy[field_name] is not None:
                field_type = field_meta.get('type')
                
                if field_type in ['Date', 'Datetime']:
                    value = data_copy[field_name]
                    
                    # Convert strings to datetime objects
                    if isinstance(value, str):
                        try:
                            # Normalize date string format
                            normalized_str = value.strip()
                            if 'T' not in normalized_str and ' ' not in normalized_str:
                                # Add time component if just date (YYYY-MM-DD)
                                if len(normalized_str) == 10 and normalized_str.count('-') == 2:
                                    normalized_str = f"{normalized_str}T00:00:00"
                            
                            # Handle timezone indicators
                            if normalized_str.endswith('Z'):
                                normalized_str = normalized_str[:-1] + '+00:00'
                                
                            data_copy[field_name] = datetime.fromisoformat(normalized_str)
                        except (ValueError, TypeError):
                            # Leave as-is if parsing fails
                            pass
                    elif isinstance(value, datetime):
                        # For 'Date' fields, normalize to start of day in UTC for consistency
                        if field_type == 'Date':
                            date_part = value.date()
                            data_copy[field_name] = datetime.combine(date_part, datetime.min.time(), timezone.utc)
                        # For 'Datetime' fields, keep as-is
        
        return data_copy
    
    def _process_datetime_fields_for_retrieval(self, data: Dict[str, Any], entity_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ensure datetime fields are proper Python datetime objects after retrieval from database."""
        if not entity_metadata or 'fields' not in entity_metadata:
            return data
            
        data_copy = data.copy()
        fields_metadata = entity_metadata['fields']
        
        for field_name, field_meta in fields_metadata.items():
            if field_name in data_copy and data_copy[field_name] is not None:
                field_type = field_meta.get('type')
                
                if field_type in ['Date', 'Datetime']:
                    value = data_copy[field_name]
                    
                    # Ensure we return Python datetime objects
                    if isinstance(value, str):
                        try:
                            # Handle timezone indicators
                            if value.endswith('Z'):
                                value = value[:-1] + '+00:00'
                            data_copy[field_name] = datetime.fromisoformat(value)
                        except (ValueError, TypeError):
                            # Leave as-is if parsing fails
                            pass
                    # If it's already a datetime object, keep as-is
        
        return data_copy

    @abstractmethod
    async def prepare_document_for_save(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None, entity_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare document for save (datetime conversion, synthetic indexes for ES, etc.)"""
        pass
    
    @abstractmethod
    async def validate_unique_constraints_before_save(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> None:
        """Validate unique constraints before saving (native for MongoDB, synthetic for ES)"""
        pass
    
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
    
    

