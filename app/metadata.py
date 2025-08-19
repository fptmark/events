"""
Entity Metadata Management

Centralized metadata handling for entity names, field names, and mappings.
Provides case-insensitive lookups and proper name resolution.
"""

from typing import Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass


@dataclass
class FieldInfo:
    """Information about a specific field"""
    name: str  # Actual field name with proper casing
    type: str  # Field type (String, Integer, etc.)
    required: bool = False
    auto_generate: bool = False
    auto_update: bool = False
    enum_values: Optional[Set[str]] = None
    
    @classmethod
    def from_metadata(cls, name: str, field_data: Dict[str, Any]) -> 'FieldInfo':
        """Create FieldInfo from metadata dictionary"""
        return cls(
            name=name,
            type=field_data.get('type', 'String'),
            required=field_data.get('required', False),
            auto_generate=field_data.get('autoGenerate', False),
            auto_update=field_data.get('autoUpdate', False),
            enum_values=set(field_data.get('enum', [])) if 'enum' in field_data else None
        )


class EntityMetadata:
    """Centralized metadata management for entities"""
    
    def __init__(self, entity_name: str, metadata: Dict[str, Any]):
        """
        Initialize entity metadata
        
        Args:
            entity_name: Proper cased entity name (e.g., "User")
            metadata: Raw metadata dictionary from model
        """
        self.entity_name = entity_name
        self.raw_metadata = metadata or {}
        
        # Build field information
        self.fields: Dict[str, FieldInfo] = {}
        fields_data = self.raw_metadata.get('fields', {})
        for field_name, field_data in fields_data.items():
            self.fields[field_name] = FieldInfo.from_metadata(field_name, field_data)
        
        # Build case-insensitive mappings
        self._entity_mapping: Dict[str, str] = {}
        self._field_mapping: Dict[str, str] = {}
        self._build_mappings()
    
    def _build_mappings(self) -> None:
        """Build case-insensitive mappings for entity and field names"""
        # Entity mapping: lowercase -> proper case
        self._entity_mapping[self.entity_name.lower()] = self.entity_name
        
        # Field mappings: lowercase -> proper case
        for field_name in self.fields.keys():
            self._field_mapping[field_name.lower()] = field_name
    
    def get_entity_name(self, lowercase_name: str) -> Optional[str]:
        """Get properly cased entity name from lowercase input"""
        return self._entity_mapping.get(lowercase_name.lower())
    
    def get_field_name(self, lowercase_name: str) -> Optional[str]:
        """Get properly cased field name from lowercase input"""
        return self._field_mapping.get(lowercase_name.lower())
    
    def get_field_info(self, field_name: str) -> Optional[FieldInfo]:
        """Get field information, supporting case-insensitive lookup"""
        # Try exact match first
        if field_name in self.fields:
            return self.fields[field_name]
        
        # Try case-insensitive match
        proper_name = self.get_field_name(field_name)
        if proper_name:
            return self.fields[proper_name]
        
        return None
    
    def is_valid_field(self, field_name: str) -> bool:
        """Check if field name is valid (case-insensitive)"""
        return self.get_field_info(field_name) is not None
    
    def is_enum_field(self, field_name: str) -> bool:
        """Check if field has enum values defined"""
        field_info = self.get_field_info(field_name)
        return field_info is not None and field_info.enum_values is not None
    
    def is_unique_field(self, field_name: str) -> bool:
        """Check if field is part of unique constraints"""
        field_info = self.get_field_info(field_name)
        if not field_info:
            return False
        
        try:
            unique_constraints = self.raw_metadata.get('uniques', [])
            proper_name = field_info.name
            for constraint in unique_constraints:
                if constraint and hasattr(constraint, '__iter__') and proper_name in constraint:
                    return True
        except (AttributeError, TypeError):
            pass
        
        return False
    
    def is_auto_generated_field(self, field_name: str) -> bool:
        """Check if field is auto-generated or auto-updated"""
        field_info = self.get_field_info(field_name)
        if not field_info:
            return False
        return field_info.auto_generate or field_info.auto_update
    
    def get_default_sort_field(self) -> str:
        """Get default sort field - first auto-generated date field or fallback"""
        # Look for auto-generated date/datetime fields
        for field_info in self.fields.values():
            if (field_info.auto_generate and 
                field_info.type in ['Date', 'Datetime']):
                return field_info.name
        
        # Fallback to createdAt (should exist on all entities)
        return 'createdAt'
    
    
    def should_use_partial_matching(self, field_name: str) -> bool:
        """Determine if field should use partial matching for filtering"""
        field_info = self.get_field_info(field_name)
        if not field_info:
            return False
        
        # Only String fields without enum use partial matching
        return field_info.type == 'String' and field_info.enum_values is None
    


class MetadataManager:
    """Static metadata manager for caching entity metadata"""
    
    # Class variables for static storage
    _cache: Dict[str, EntityMetadata] = {}
    _entity_name_registry: Dict[str, str] = {}  # lowercase -> proper case
    
    @classmethod
    def register_entity(cls, entity_name: str, raw_metadata: Dict[str, Any]) -> EntityMetadata:
        """Register entity metadata permanently (static)"""
        cache_key = entity_name.lower()
        
        # Register entity name mapping
        cls._entity_name_registry[cache_key] = entity_name
        
        # Create and cache metadata if not exists
        if cache_key not in cls._cache:
            cls._cache[cache_key] = EntityMetadata(entity_name, raw_metadata)
        
        return cls._cache[cache_key]
    
    @classmethod
    def get_entity_metadata(cls, entity_name: str) -> Optional[EntityMetadata]:
        """Get cached entity metadata"""
        cache_key = entity_name.lower()
        return cls._cache.get(cache_key)
    
    @classmethod
    def get_proper_entity_name(cls, entity_name: str) -> str:
        """Get properly cased entity name from registry"""
        if not entity_name:
            return entity_name
        
        cache_key = entity_name.lower()
        return cls._entity_name_registry.get(cache_key, entity_name.capitalize())
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear metadata cache (useful for testing)"""
        cls._cache.clear()
        cls._entity_name_registry.clear()


def register_entity_metadata(entity_name: str, raw_metadata: Dict[str, Any]) -> EntityMetadata:
    """Register entity metadata globally (called during model loading)"""
    return MetadataManager.register_entity(entity_name, raw_metadata)


def get_entity_metadata(entity_name: str) -> Optional[EntityMetadata]:
    """Get cached entity metadata"""
    return MetadataManager.get_entity_metadata(entity_name)


def get_proper_entity_name(entity_name: str) -> str:
    """Get properly cased entity name from global registry"""
    return MetadataManager.get_proper_entity_name(entity_name)


def clear_metadata_cache() -> None:
    """Clear the global metadata cache"""
    MetadataManager.clear_cache()