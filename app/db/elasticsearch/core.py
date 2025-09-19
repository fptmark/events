"""
Elasticsearch core, entity, and index operations implementation.
Contains ElasticsearchCore, ElasticsearchEntities, and ElasticsearchIndexes classes.
"""

import logging
from typing import Any, Dict, List, Optional
from elasticsearch import AsyncElasticsearch

from ..core_manager import CoreManager
from ..entity_manager import EntityManager
from ..index_manager import IndexManager
from app.services.metadata import MetadataService


class ElasticsearchCore(CoreManager):
    """Elasticsearch implementation of core operations"""
    
    def __init__(self, parent):
        self.parent = parent
        self._client: Optional[AsyncElasticsearch] = None
        self._database_name: str = ""
    
    @property
    def id_field(self) -> str:
        return "_id"
    
    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize Elasticsearch connection"""
        if self._client is not None:
            logging.info("ElasticsearchDatabase: Already initialized")
            return

        self._client = AsyncElasticsearch([connection_str])
        self._database_name = database_name
        
        # Test connection
        await self._client.ping()
        self.parent._initialized = True
        logging.info(f"ElasticsearchDatabase: Connected to {database_name}")
        
        # Create index template for .raw subfields on all new indices
        await self._ensure_index_template()
    
    async def close(self) -> None:
        """Close Elasticsearch connection"""
        if self._client:
            await self._client.close()
            self._client = None
            self.parent._initialized = False
            logging.info("ElasticsearchDatabase: Connection closed")
    
    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize ID from Elasticsearch document"""
        if not document:
            return None
        
        id_value = document.get(self.id_field)
        if id_value is None:
            return None
            
        # Elasticsearch _id is already a string, just return it
        return str(id_value) if id_value else None
    
    def get_connection(self) -> AsyncElasticsearch:
        """Get Elasticsearch client instance"""
        if not self._client:
            raise RuntimeError("Elasticsearch not initialized")
        return self._client
    
    async def _ensure_index_template(self) -> None:
        """Create composable index template for .raw subfields with high priority."""
        # Get entity names from metadata service to determine index patterns
        entities = MetadataService.list_entities()
        index_patterns = [entity.lower() for entity in entities] if entities else ["*"]
        
        template_name = "app-text-raw-template"
        template_body = {
            "index_patterns": index_patterns,
            "priority": 1000,  # Higher priority than default templates
            "template": {
                "settings": {
                    "analysis": {
                        "normalizer": {
                            "lc": {
                                "type": "custom",
                                "char_filter": [],
                                "filter": ["lowercase"]
                            }
                        }
                    }
                },
                "mappings": {
                    "dynamic_templates": [
                        {
                            "strings_as_text_with_raw": {
                                "match_mapping_type": "string",
                                "unmatch": "id",  # Don't apply to id fields
                                "mapping": {
                                    "type": "text",
                                    "fields": {
                                        "raw": {
                                            "type": "keyword",
                                            "normalizer": "lc",
                                            "ignore_above": 1024
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        await self._client.indices.put_index_template(name=template_name, body=template_body) # type: ignore
        logging.info(f"Created index template: {template_name}")


class ElasticsearchEntities(EntityManager):
    """Elasticsearch implementation of entity operations"""
    
    def __init__(self, parent):
        self.parent = parent
    
    async def exists(self, entity_type: str) -> bool:
        """Check if index exists"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()

        return await es.indices.exists(index=entity_type.lower())
    
    async def create(self, entity_type: str, unique_constraints: List[List[str]]) -> bool:
        """Create index (Elasticsearch doesn't enforce unique constraints natively)"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()

        if await es.indices.exists(index=entity_type.lower()):
            return True

        await es.indices.create(index=entity_type.lower())
        return True
    
    async def delete(self, entity_type: str) -> bool:
        """Delete index"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()

        if await es.indices.exists(index=entity_type.lower()):
            await es.indices.delete(index=entity_type.lower())
        return True
    
    async def get_all(self) -> List[str]:
        """Get all index names"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        response = await es.cat.indices(format="json")
        return [index["index"] for index in response]


class ElasticsearchIndexes(IndexManager):
    """Elasticsearch implementation of index operations (limited functionality)"""
    
    def __init__(self, parent):
        self.parent = parent
    
    async def create(
        self, 
        entity_type: str, 
        fields: List[str],
        unique: bool = False,
        name: Optional[str] = None
    ) -> None:
        """Create synthetic unique constraint mapping for Elasticsearch"""
        if not unique:
            return  # Only handle unique constraints
            
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        properties: Dict[str, Any] = {}
        
        # Ensure index exists
        if not await es.indices.exists(index=entity_type.lower()):
            await es.indices.create(index=entity_type.lower())
        
        if len(fields) == 1:
            # Single field unique constraint - ensure it has .raw subfield for exact matching
            field_name = fields[0]
            properties = {
                field_name: {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                }
            }
        else:
            # Multi-field unique constraint - create hash field
            hash_field_name = f"_hash_{'_'.join(sorted(fields))}"
            properties = {
                hash_field_name: {
                    "type": "keyword"
                }
            }
            # Also ensure all individual fields have proper mapping
            for field_name in fields:
                properties[field_name] = {
                    "type": "text",
                    "fields": {
                        "raw": {
                            "type": "keyword", 
                            "ignore_above": 256
                        }
                    }
                }
        
        # Update mapping
        await es.indices.put_mapping(
            index=entity_type.lower(),
            properties=properties
        )
    
    async def get_all(self, entity_type: str) -> List[List[str]]:
        """Get synthetic unique indexes (hash fields) for Elasticsearch"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        if not await es.indices.exists(index=entity_type.lower()):
            return []
        
        # For Elasticsearch, we look for hash fields that represent unique constraints
        # Hash fields follow pattern: _hash_field1_field2_... for multi-field constraints
        response = await es.indices.get_mapping(index=entity_type.lower())
        mapping = response.get(entity_type.lower(), {}).get("mappings", {}).get("properties", {})
        
        unique_constraints = []
        processed_fields = set()
        
        for field_name in mapping.keys():
            if field_name.startswith('_hash_'):
                # This is a hash field for multi-field unique constraint
                # Extract original field names from hash field name
                # Format: _hash_field1_field2_...
                fields_part = field_name[6:]  # Remove '_hash_'
                original_fields = fields_part.split('_')
                if len(original_fields) > 1:
                    unique_constraints.append(original_fields)
                    processed_fields.update(original_fields)
            elif field_name not in processed_fields:
                # Single field that might have unique constraint
                # Check if it's a .raw field (which indicates unique constraint setup)
                field_config = mapping[field_name]
                if (isinstance(field_config, dict) and 
                    'fields' in field_config and 
                    'raw' in field_config['fields']):
                    # This field has unique constraint
                    unique_constraints.append([field_name])
        
        return unique_constraints
    
    async def delete(self, entity_type: str, fields: List[str]) -> None:
        """Delete synthetic unique constraint (limited in Elasticsearch)"""
        # Elasticsearch doesn't allow removing fields from existing mappings
        # In practice, you'd need to reindex to a new index without these fields
        # For now, this is a no-op as field removal requires complex reindexing
        
        # Note: In a full implementation, this would:
        # 1. Create new index without the constraint fields/hash fields
        # 2. Reindex all data from old to new index  
        # 3. Delete old index and alias new index to old name
        # This is complex and not commonly done in production
        pass