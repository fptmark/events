from typing import Dict, List, Any, Optional, Tuple
from app.services.notify import Notification, HTTP
from app.utils import merge_overrides

class MetadataService:
    _metadata: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def initialize(entities: List[str]) -> None:
        """Initialize the metadata service with entity list."""
        MetadataService._metadata = {}
        for entity in entities:
            md = MetadataService._get_raw_metadata(entity)
            if not md:
                MetadataService._fail_fast(f"No metadata found for entity {entity}")
            # Apply overrides to the metadata
            merged_md = merge_overrides(entity, md.copy()) # type: ignore
            merged_md['fields']['id'] = {'type': 'ObjectId', 'required': True}
            MetadataService._metadata[entity] = merged_md
     
    @staticmethod
    def list_entities() -> List[str]:
        """List all entities with metadata."""
        return list(MetadataService._metadata.keys())

    @staticmethod
    def get(entity: str, field: Optional[str] = None, attribute: Optional[str] = None) -> Any:
        """Get metadata with fail-fast error handling."""
        # find metadata where lower key = entity.lower()
        found = False
        for e, metadata in MetadataService._metadata.items():
            if e.lower() == entity.lower():
                found = True
                break
        if not found:
            return None
        #     MetadataService._fail_fast(f"Entity metadata not found: {entity}")
            
        if field is None:
            return metadata

        # find field in metadata
        fields = metadata.get('fields', {})
        found = False
        for f, fd in fields.items():
            if f.lower() == field.lower():
                found = True
                break
                
        if not found:
            return None
            # MetadataService._fail_fast(f"Field metadata not found: {entity}.{field}")
            
        if attribute is None:
            return fd
        
        # Get nested attribute with dot notation
        attrs = attribute.split('.')
        ad: Dict[str, Any] = fd
        for attr in attrs:
            if not isinstance(ad, dict):
                MetadataService._fail_fast(f"Invalid attribute path at '{attr}' in {entity}.{field}.{attribute} - not a dictionary")
            if attr not in ad:
                MetadataService._fail_fast(f"Attribute '{attr}' not found in {entity}.{field}.{attribute}")
            ad = ad[attr]
        return ad

    @staticmethod
    def fields(entity: str) -> Dict[str, Any]:
        """Get all fields metadata for an entity."""
        metadata = MetadataService.get(entity)
        return metadata.get('fields', {}) if metadata else {}

    @staticmethod
    def get_proper_name(entity: str, field: Optional[str] = None) -> str:
        #id is a special case
        if field and field.lower() == 'id':
            return 'id'

        # find metadata where lower key = entity.lower()
        for e, md in MetadataService._metadata.items():
            if e.lower() == entity.lower():
                if field:
                    for f in md.get('fields', {}):
                        if f.lower() == field.lower():
                            return f
                else:
                    return e
        return ''

    @staticmethod
    def _get_raw_metadata(entity: str) -> Optional[Dict[str, Any]]:
        
        module_path = f"app.models.{entity.lower()}_model.{entity}"
        if not module_path:
            return None
            
        try:
            module_name, class_name = module_path.rsplit('.', 1)
            module = __import__(module_name, fromlist=[class_name])
            entity_class = getattr(module, class_name)
            return entity_class._metadata
        except (ImportError, AttributeError) as e:
            MetadataService._fail_fast(f"Failed to import or get metadata from {module_path}: {e}")
            return None
    
    @staticmethod
    def _fail_fast(message: str) -> None:
        """Fail-fast error handling - notify and raise exception."""
        Notification.error(HTTP.INTERNAL_ERROR, message)
        raise ValueError(message)