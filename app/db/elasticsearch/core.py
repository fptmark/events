"""
Elasticsearch core, entity, and index operations implementation.
Contains ElasticsearchCore, ElasticsearchEntities, ElasticsearchIndexes and ElasticsearchDatabase classes.
"""

import logging
import sys
from typing import Any, Dict, List, Optional
from elasticsearch import AsyncElasticsearch

from ..base import DatabaseInterface
from ..core_manager import CoreManager
from ..index_manager import IndexManager
from app.services.metadata import MetadataService


class ElasticsearchCore(CoreManager):
    """Elasticsearch implementation of core operations"""

    # Expected template structure for validation
    EXPECTED_TEMPLATE = {
        "priority": 1000,
        "template": {
            "settings": {
                "index": {
                    "analysis": {
                        "normalizer": {
                            "lc": {
                                "type": "custom",
                                "char_filter": [],
                                "filter": ["lowercase"]
                            }
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {
                        "type": "keyword"
                    }
                },
                "dynamic_templates": [
                    {
                        "strings_as_keyword": {
                            "unmatch": "id",
                            "mapping": {
                                "normalizer": "lc",
                                "type": "keyword"
                            },
                            "match_mapping_type": "string"
                        }
                    }
                ]
            }
        }
    }

    def __init__(self, database):
        super().__init__(database)
        self._client: Optional[AsyncElasticsearch] = None
        self._database_name: str = ""
    
    @property
    def id_field(self) -> str:
        return "id"
    
    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize Elasticsearch connection"""
        if self._client is not None:
            logging.info("ElasticsearchDatabase: Already initialized")
            return

        self._client = AsyncElasticsearch([connection_str])
        self._database_name = database_name

        # Test connection
        await self._client.ping()
        self.database._initialized = True
        logging.info(f"ElasticsearchDatabase: Connected to {database_name}")

        # Create index template for simplified keyword approach
        await self._ensure_index_template()

        # Validate existing mappings and set health state
        await self._validate_mappings_and_set_health()
    
    async def close(self) -> None:
        """Close Elasticsearch connection"""
        if self._client:
            await self._client.close()
            self.database._initialized = False
            logging.info("ElasticsearchDatabase: Connection closed")

    def _get_default_sort_field(self, entity: str) -> str:
        """For Elasticsearch, always use _id as the default sort field"""
        return self.id_field
    
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
        if self._client is not None and self._client.indices is not None:
            try:
                conflicting_templates = await self._client.indices.get_index_template(name="app-text-raw-template")
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

            # Use the EXPECTED_TEMPLATE with dynamic index patterns
            template_body = {
                "index_patterns": index_patterns,
                **self.EXPECTED_TEMPLATE
            }

            await self._client.indices.put_index_template(name=template_name, body=template_body) # type: ignore
            logging.info(f"Created index template: {template_name}")

    async def _validate_mappings_and_set_health(self) -> None:
        """Validate mappings and template state, set health accordingly without terminating."""
        if self._client is not None and self._client.indices is not None:
            try:
                # Check for template conflicts first
                template_conflict = False
                try:
                    old_template = await self._client.indices.get_index_template(name="app-text-raw-template")
                    if old_template.get("index_templates"):
                        template_conflict = True
                        logging.warning("Old template 'app-text-raw-template' exists alongside new template")
                except:
                    pass

                # Get all current indices for mapping validation
                try:
                    indices_response = await self._client.cat.indices(format="json")
                    if indices_response:
                        index_names = []
                        for idx in indices_response:
                            if isinstance(idx, dict) and "index" in idx:
                                index_name = idx.get('index', None)
                                if isinstance(index_name, str) and not index_name.startswith("."):
                                    index_names.append(index_name)
                    else:
                        index_names = []
                except Exception as e:
                    logging.warning(f"Could not list indices for validation: {e}")
                    self.database._health_state = "degraded"
                    return

                violations = []

                for index_name in index_names:
                    try:
                        # Get mapping for this index
                        response = await self._client.indices.get_mapping(index=index_name)
                        properties = response.get(index_name, {}).get("mappings", {}).get("properties", {})

                        # Check each field follows our template rules
                        for field, field_mapping in properties.items():
                            # Skip ID fields (not covered by our template)
                            if field in ["id", "_id"]:
                                continue

                            # Check if this is a string field that should follow our template
                            if field_mapping.get("type") == "text" and "fields" in field_mapping:
                                violations.append(f"{index_name}.{field}: uses old text+.raw mapping")
                            elif field_mapping.get("type") == "keyword" and field_mapping.get("normalizer") != "lc":
                                violations.append(f"{index_name}.{field}: keyword field missing 'lc' normalizer")

                    except Exception as e:
                        logging.warning(f"Could not validate mapping for {index_name}: {e}")
                        continue

                # Set health state based on findings
                if template_conflict:
                    self.database._health_state = "conflict"
                    logging.warning(f"DATABASE HEALTH: CONFLICT - Template conflicts detected")
                elif len(violations) > 0:
                    self.database._health_state = "degraded"
                    logging.warning(f"DATABASE HEALTH: DEGRADED - Found {len(violations)} mapping violations:")
                    for violation in violations:
                        logging.warning(f"  {violation}")
                    logging.warning("Use /api/db/init to recreate indices with correct mappings")
                else:
                    self.database._health_state = "healthy"
                    logging.info("DATABASE HEALTH: HEALTHY - All mappings compatible with template")

            except Exception as e:
                logging.error(f"Health validation failed: {e}")
                self.database._health_state = "degraded"


    async def wipe_and_reinit(self) -> bool:
        """Completely wipe all indices and reinitialize with correct mappings"""
        try:
            self.database._ensure_initialized()
            es = self.get_connection()

            # Get all current indices (excluding system indices)
            indices_response = await es.cat.indices(format="json")
            if indices_response:
                user_indices = []
                for idx in indices_response:
                    if isinstance(idx, dict) and "index" in idx:
                        index_name = idx.get('index', None)
                        if isinstance(index_name, str) and not index_name.startswith("."):
                            user_indices.append(index_name)
            else:
                user_indices = []

            # Delete all user indices
            for index_name in user_indices:
                try:
                    await es.indices.delete(index=index_name)
                except Exception:
                    # Index might not exist, that's fine
                    pass

            # Delete old template if it exists
            try:
                await es.indices.delete_index_template(name="app-text-raw-template")
            except Exception:
                # Template might not exist, that's fine
                pass
            try:
                await es.indices.delete_index_template(name="app-keyword-template")
            except Exception:
                # Template might not exist, that's fine
                pass

            # Recreate template with current settings
            await self._ensure_index_template()

            # Reset health state to healthy after successful cleanup
            self.database._health_state = "healthy"

            return True

        except Exception as e:
            logging.error(f"Database wipe and reinit failed: {e}")
            return False

    async def get_status_report(self) -> dict:
        """Get comprehensive database status including mapping validation"""
        try:
            self.database._ensure_initialized()
            es = self.get_connection()

            # Get cluster info
            cluster_info = await es.info()

            # Get all indices
            indices_response = await es.cat.indices(format="json")
            user_indices = []
            if indices_response:
                for idx in indices_response:
                    if isinstance(idx, dict) and "index" in idx:
                        index_name = idx.get("index", None)
                        if isinstance(index_name, str) and not index_name.startswith("."):
                            user_indices.append(idx)

            # Check mappings for violations
            violations = []
            indices_details = {}

            for idx in user_indices:
                # idx is guaranteed to be a dict with "index" key from filtering above
                index_name = str(idx["index"])
                doc_count = int(idx["docs.count"]) if idx.get("docs.count") else 0
                store_size = str(idx["store.size"]) if idx.get("store.size") else "0b"

                try:
                    # Get mapping
                    mapping_response = await es.indices.get_mapping(index=index_name)
                    properties = mapping_response.get(index_name, {}).get("mappings", {}).get("properties", {})

                    # Analyze each field
                    fields = {}
                    for field, field_mapping in properties.items():
                        if field in ["id", "_id"]:
                            continue

                        field_status = "ok"
                        es_type = field_mapping.get("type", "unknown")

                        # Get schema type and enum info from metadata
                        schema_type = "unknown"
                        is_enum = False
                        try:
                            from app.services.metadata import MetadataService
                            # Get entity name from index name (capitalize first letter)
                            entity_name = index_name.capitalize()
                            schema_type = MetadataService.get(entity_name, field, 'type') or "unknown"
                            field_metadata = MetadataService.get(entity_name, field)
                            if field_metadata:
                                is_enum = "enum" in field_metadata
                        except:
                            pass

                        # Format type display as es_type/schema_type
                        type_display = f"{es_type}/{schema_type}"

                        # Check for violations
                        if field_mapping.get("type") == "text" and "fields" in field_mapping:
                            field_status = "uses old text+.raw mapping"
                            violations.append(f"{index_name}.{field}: {field_status}")
                        elif field_mapping.get("type") == "keyword" and field_mapping.get("normalizer") != "lc":
                            field_status = "keyword field missing 'lc' normalizer"
                            violations.append(f"{index_name}.{field}: {field_status}")

                        # Get field statistics
                        population = "0%"
                        approx_uniques = "0%"

                        if doc_count > 0:
                            try:
                                # Get field stats using exists query for population
                                exists_query = {
                                    "query": {"exists": {"field": field}},
                                    "size": 0
                                }
                                exists_response = await es.search(index=index_name, body=exists_query)
                                non_null_count = exists_response.get("hits", {}).get("total", {}).get("value", 0)
                                population_pct = int((non_null_count / doc_count) * 100)
                                population = f"{population_pct}%"

                                # Get cardinality using cardinality aggregation
                                if non_null_count > 0:
                                    # With keyword+lc normalizer, query fields directly
                                    cardinality_query = {
                                        "aggs": {
                                            "unique_count": {
                                                "cardinality": {"field": field}
                                            }
                                        },
                                        "size": 0
                                    }
                                    cardinality_response = await es.search(index=index_name, body=cardinality_query)
                                    unique_count = cardinality_response.get("aggregations", {}).get("unique_count", {}).get("value", 0)
                                    if unique_count > 0:
                                        cardinality_pct = int((unique_count / non_null_count) * 100)
                                        approx_uniques = f"{cardinality_pct}%"

                            except Exception as stats_error:
                                # Stats failed, use defaults
                                logging.warning(f"Field stats failed for {index_name}.{field}: {stats_error}")

                        # For enums, flag high uniqueness as potential issue
                        approx_uniques_display = approx_uniques
                        if is_enum and approx_uniques != "0%":
                            # Extract percentage value for comparison
                            uniques_pct = int(approx_uniques.rstrip('%'))
                            if uniques_pct > 50:
                                approx_uniques_display = f"🔴{approx_uniques}"

                        fields[field] = {
                            "es type/yaml type": type_display,
                            "status": field_status,
                            "population": population,
                            "approx_uniques": approx_uniques_display,
                            "is_enum": is_enum
                        }

                    indexes = await self.database.indexes.get_all_detailed(index_name.capitalize())
                    indices_details[index_name] = {
                        "doc_count": doc_count,
                        "store_size": store_size,
                        "fields": fields,
                        "indexes": indexes
                    }

                except Exception as e:
                    indices_details[index_name] = {
                        "error": f"Could not analyze: {str(e)}"
                    }

            # Check template status - verify it matches expected structure
            try:
                template_response = await es.indices.get_index_template(name="app-keyword-template")
                if len(template_response.get("index_templates", [])) > 0:
                    # Template exists, check core structure (ignore index_patterns)
                    actual = template_response["index_templates"][0]["index_template"]["template"]
                    expected = self.EXPECTED_TEMPLATE["template"]
                    template_ok = actual == expected
                else:
                    template_ok = False
            except:
                template_ok = False

            # Determine overall status
            if not template_ok or len(violations) > 0:
                status = "degraded"
            else:
                status = "success"

            # Create standardized entities dict for testing
            entities = {}
            for index_name, details in indices_details.items():
                if "error" not in details:
                    # Capitalize index name to match entity naming convention
                    entity_name = index_name.capitalize()
                    doc_count = details.get("doc_count", 0)
                    entities[entity_name] = doc_count

            return {
                "database": "elasticsearch",
                "status": status,
                "entities": entities,
                "details": {
                    "template_ok": template_ok,
                    "cluster": {
                        "name": cluster_info.get("cluster_name", "unknown"),
                        "version": cluster_info.get("version", {}).get("number", "unknown")
                    },
                    "indices": {
                        "total": len(user_indices),
                        "details": indices_details
                    },
                    "mappings": {
                        "violations_count": len(violations),
                        "violations": violations
                    }
                }
            }

        except Exception as e:
            return {
                "database": "elasticsearch",
                "status": "error",
                "entities": {},
                "error": str(e)
            }


class ElasticsearchIndexes(IndexManager):
    """Elasticsearch implementation of index operations (limited functionality)"""

    def __init__(self, database):
        super().__init__(database)
    
    async def create(
        self,
        entity: str,
        fields: List[str],
        unique: bool = False,
        name: Optional[str] = None
    ) -> None:
        """Create synthetic unique constraint mapping for Elasticsearch

        Note: With the new keyword+lc normalizer template, fields are automatically
        created with the correct mapping when documents are indexed. This method
        is kept for consistency with the IndexManager interface but doesn't need
        to create explicit mappings since the template handles it.
        """
        if not unique:
            return  # Only handle unique constraints

        self.database._ensure_initialized()
        es = self.database.core.get_connection()

        # Ensure index exists - template will apply keyword+lc normalizer automatically
        if not await es.indices.exists(index=entity.lower()):
            await es.indices.create(index=entity.lower())

        # For multi-field unique constraints, create hash field with lc normalizer
        if len(fields) > 1:
            hash_field = f"_hash_{'_'.join(sorted(fields))}"
            properties = {
                hash_field: {
                    "type": "keyword",
                    "normalizer": "lc"
                }
            }
            await es.indices.put_mapping(
                index=entity.lower(),
                properties=properties
            )

        # Single-field constraints don't need explicit mapping - template handles it
    
    async def get_all(self, entity: str) -> List[List[str]]:
        """Get synthetic unique indexes from metadata and verify they exist in the index

        With the new keyword+lc normalizer template, unique constraint fields are just
        regular keyword fields. We get the expected unique constraints from metadata
        and verify they exist in the index mapping.
        """
        self.database._ensure_initialized()
        es = self.database.core.get_connection()

        # Get expected unique constraints from metadata
        metadata = MetadataService.get(entity)
        expected_uniques = metadata.get('uniques', [])

        if not await es.indices.exists(index=entity.lower()):
            # Index doesn't exist yet - return empty list
            # (create() will create the index when called)
            return []

        # Get current mapping
        response = await es.indices.get_mapping(index=entity.lower())
        mapping = response.get(entity.lower(), {}).get("mappings", {}).get("properties", {})

        # Check which unique constraints are set up
        existing_constraints = []

        for constraint_fields in expected_uniques:
            if len(constraint_fields) == 1:
                # Single field - check if it exists in mapping
                field = constraint_fields[0]
                if field in mapping:
                    existing_constraints.append(constraint_fields)
            else:
                # Multi-field - check if hash field exists
                hash_field = f"_hash_{'_'.join(sorted(constraint_fields))}"
                if hash_field in mapping:
                    # Also verify all individual fields exist
                    if all(field in mapping for field in constraint_fields):
                        existing_constraints.append(constraint_fields)

        return existing_constraints

    async def get_all_detailed(self, entity: str) -> dict:
        """Get all synthetic unique constraints from metadata"""
        from app.services.metadata import MetadataService

        indexes = {}
        try:
            metadata = MetadataService.get(entity)
            uniques = metadata.get('uniques', [])

            for fields in uniques:
                index_name = "_".join(fields) + "_unique"
                indexes[index_name] = {
                    "fields": fields,
                    "unique": True,
                    "sparse": False,
                    "type": "synthetic"
                }
        except Exception as e:
            self.logger.error(f"Elasticsearch get detailed indexes error: {str(e)}")

        return indexes

    async def delete(self, entity: str, fields: List[str]) -> None:
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


class ElasticsearchDatabase(DatabaseInterface):
    """Elasticsearch implementation of DatabaseInterface"""

    def _get_manager_classes(self) -> dict:
        """Return Elasticsearch manager classes"""
        from .documents import ElasticsearchDocuments

        return {
            'core': ElasticsearchCore,
            'documents': ElasticsearchDocuments,
            'indexes': ElasticsearchIndexes
        }

    def supports_native_indexes(self) -> bool:
        """Elasticsearch does not support native unique indexes"""
        return False