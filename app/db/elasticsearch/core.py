"""
Elasticsearch core, entity, and index operations implementation.
Contains ElasticsearchCore, ElasticsearchEntities, and ElasticsearchIndexes classes.
"""

import logging
import sys
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

        # Create index template for simplified keyword approach
        await self._ensure_index_template()

        # Validate existing mappings and set health state
        await self._validate_mappings_and_set_health()
    
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
        """Create composable index template for simplified keyword approach with high priority."""
        # Check for conflicting templates first
        try:
            conflicting_templates = await self._client.indices.get_index_template(name="app-text-raw-template", ignore=[404])
            if conflicting_templates.get("index_templates"):
                raise RuntimeError("Conflicting template 'app-text-raw-template' exists. Use /api/db/init to clean up old templates.")
        except Exception as e:
            if "Conflicting template" in str(e):
                raise
            # Other errors (like 404) are fine - template doesn't exist

        # Get entity names from metadata service to determine index patterns
        entities = MetadataService.list_entities()
        index_patterns = [entity.lower() for entity in entities] if entities else ["*"]

        template_name = "app-keyword-template"
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
                            "strings_as_keyword": {
                                "match_mapping_type": "string",
                                "unmatch": "id",  # Don't apply to id fields
                                "mapping": {
                                    "type": "keyword",
                                    "normalizer": "lc"
                                }
                            }
                        }
                    ]
                }
            }
        }

        await self._client.indices.put_index_template(name=template_name, body=template_body) # type: ignore
        logging.info(f"Created index template: {template_name}")

    async def _validate_mappings_and_set_health(self) -> None:
        """Validate mappings and template state, set health accordingly without terminating."""
        try:
            # Check for template conflicts first
            template_conflict = False
            try:
                old_template = await self._client.indices.get_index_template(name="app-text-raw-template", ignore=[404])
                if old_template.get("index_templates"):
                    template_conflict = True
                    logging.warning("Old template 'app-text-raw-template' exists alongside new template")
            except:
                pass

            # Get all current indices for mapping validation
            try:
                indices_response = await self._client.cat.indices(format="json")
                index_names = [idx["index"] for idx in indices_response if not idx["index"].startswith(".")]
            except Exception as e:
                logging.warning(f"Could not list indices for validation: {e}")
                self.parent._health_state = "degraded"
                return

            violations = []

            for index_name in index_names:
                try:
                    # Get mapping for this index
                    response = await self._client.indices.get_mapping(index=index_name)
                    properties = response.get(index_name, {}).get("mappings", {}).get("properties", {})

                    # Check each field follows our template rules
                    for field_name, field_mapping in properties.items():
                        # Skip ID fields (not covered by our template)
                        if field_name in ["id", "_id"]:
                            continue

                        # Check if this is a string field that should follow our template
                        if field_mapping.get("type") == "text" and "fields" in field_mapping:
                            violations.append(f"{index_name}.{field_name}: uses old text+.raw mapping")
                        elif field_mapping.get("type") == "keyword" and field_mapping.get("normalizer") != "lc":
                            violations.append(f"{index_name}.{field_name}: keyword field missing 'lc' normalizer")

                except Exception as e:
                    logging.warning(f"Could not validate mapping for {index_name}: {e}")
                    continue

            # Set health state based on findings
            if template_conflict:
                self.parent._health_state = "conflict"
                logging.warning(f"DATABASE HEALTH: CONFLICT - Template conflicts detected")
            elif len(violations) > 0:
                self.parent._health_state = "degraded"
                logging.warning(f"DATABASE HEALTH: DEGRADED - Found {len(violations)} mapping violations:")
                for violation in violations:
                    logging.warning(f"  {violation}")
                logging.warning("Use /api/db/init to recreate indices with correct mappings")
            else:
                self.parent._health_state = "healthy"
                logging.info("DATABASE HEALTH: HEALTHY - All mappings compatible with template")

        except Exception as e:
            logging.error(f"Health validation failed: {e}")
            self.parent._health_state = "degraded"


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