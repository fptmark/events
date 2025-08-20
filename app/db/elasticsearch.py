import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from elasticsearch import AsyncElasticsearch, NotFoundError as ESNotFoundError
from bson import ObjectId

from .base import DatabaseInterface, SyntheticDuplicateError
from ..errors import DatabaseError, DuplicateError, NotFoundError

class ElasticsearchDatabase(DatabaseInterface):
    """Elasticsearch implementation of DatabaseInterface."""

    def __init__(self, case_sensitive_sorting: bool = False):
        super().__init__(case_sensitive_sorting)
        self._client: Optional[AsyncElasticsearch] = None
        self._url: str = ""
    

    @property
    def id_field(self) -> str:
        """Elasticsearch uses '_id' as the internal document ID field"""
        return "_id"

    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize the ID from an Elasticsearch document"""
        if not document:
            return None
        
        # Elasticsearch uses '_id' as the internal document identifier
        # This is always present and unique within the index
        id_value = document.get('_id')
        if id_value is None:
            return None
            
        return str(id_value) if id_value else None

    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize Elasticsearch connection."""
        if self._client is not None:
            logging.info("Elasticsearch already initialised – re‑using client")
            return

        self._url, self._dbname = connection_str, database_name
        client = AsyncElasticsearch(hosts=[connection_str])

        try:
            info = await client.info()
            self._initialized = True
            self._client = client
            logging.info("Connected to Elasticsearch %s", info["version"]["number"])
            
            # Create index template for .raw subfields on all new indices
            await self._ensure_index_template()
        except Exception as e:
            self._handle_connection_error(e, database_name)

    def _get_client(self) -> AsyncElasticsearch:
        """Get the AsyncElasticsearch client instance."""
        self._ensure_initialized()
        assert self._client is not None, "Client should be initialized after _ensure_initialized()"
        return self._client
    
    def _get_internal_field_name(self, field_name: str, collection: str) -> str:
        """Get the internal ES field name - adds .raw suffix for string fields."""
        from app.metadata import get_entity_metadata, get_proper_entity_name
        entity_name = get_proper_entity_name(collection)
        entity_meta = get_entity_metadata(entity_name)
        
        if entity_meta:
            field_info = entity_meta.get_field_info(field_name)
            if field_info and field_info.type == 'String':
                return f"{field_name}.raw"
        
        return field_name
    
    async def wipe_all_index_templates(self) -> None:
        """Remove all existing index templates to avoid conflicts."""
        es = self._get_client()
        
        try:
            # Get all index templates
            templates = await es.indices.get_index_template()
            
            for template_info in templates.get('index_templates', []):
                template_name = template_info['name']
                try:
                    await es.indices.delete_index_template(name=template_name)
                    logging.info(f"Deleted index template: {template_name}")
                except Exception as e:
                    logging.warning(f"Failed to delete template {template_name}: {e}")
                    
        except Exception as e:
            logging.warning(f"Failed to wipe index templates: {e}")

    async def wipe_all_indices(self) -> None:
        """Delete application indices to force recreation with new templates."""
        from app.metadata import get_all_entity_names
        es = self._get_client()
        
        try:
            # Get entity names from metadata
            entity_names = get_all_entity_names()
            if not entity_names:
                # Fallback to known entities if metadata not loaded
                entity_names = ["User", "Account", "Profile", "TagAffinity", "Event", "UserEvent", "Url", "Crawl"]
            
            for entity_name in entity_names:
                index_name = entity_name.lower()
                try:
                    if await es.indices.exists(index=index_name):
                        await es.indices.delete(index=index_name)
                        logging.info(f"Deleted index: {index_name}")
                except Exception as e:
                    logging.warning(f"Failed to delete index {index_name}: {e}")
                        
        except Exception as e:
            logging.warning(f"Failed to wipe indices: {e}")

    async def _ensure_index_template(self) -> None:
        """Create composable index template for .raw subfields with high priority."""
        es = self._get_client()
        
        template_name = "app-text-raw-template"
        template_body = {
            "index_patterns": ["user", "account", "profile", "event*", "tag*", "url", "crawl"],  # Target our app indices only
            "priority": 1000,  # Higher priority than existing templates (beats 500)
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
        
        try:
            await es.indices.put_index_template(name=template_name, body=template_body)
            logging.info(f"Created index template: {template_name}")
        except Exception as e:
            logging.warning(f"Failed to create index template: {e}")
            # Don't fail initialization if template creation fails

    async def get_all(self, collection: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Get all documents from a collection with count."""
        es = self._get_client()

        if not await es.indices.exists(index=collection):
            return [], [], 0

        try:
            warnings = []
            # Check unique constraints if provided
            if unique_constraints:
                missing_indexes = await self._check_unique_indexes(collection, unique_constraints)
                if missing_indexes:
                    warnings.extend(missing_indexes)
            
            res = await es.search(index=collection, query={"match_all": {}}, size=1000)
            hits = res.get("hits", {}).get("hits", [])
            results = [{**hit["_source"], "id": self._normalize_id(hit["_id"])} for hit in hits]
            
            # Extract total count from search response
            total_count = res.get("hits", {}).get("total", {}).get("value", 0)
            
            return results, warnings, total_count
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_all"
            )

    async def _get_list_impl(self, collection: str, unique_constraints: Optional[List[List[str]]] = None, list_params=None, entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Get paginated/filtered list of documents from a collection with count."""
        es = self._get_client()

        if not await es.indices.exists(index=collection):
            return [], [], 0

        try:
            from app.models.list_params import ListParams
            warnings = []
            
            # Check unique constraints if provided
            if unique_constraints:
                missing_indexes = await self._check_unique_indexes(collection, unique_constraints)
                if missing_indexes:
                    warnings.extend(missing_indexes)
            
            # If no list_params provided, fall back to get_all behavior
            if not list_params:
                return await self.get_all(collection, unique_constraints)

            # Build Elasticsearch query using new helper methods
            query_filter = self._build_query_filter(list_params, entity_metadata)
            query_body = {
                "from": (list_params.page - 1) * list_params.page_size,
                "size": list_params.page_size,
                "query": query_filter
            }
            
            # Always add sorting for consistent pagination
            sort_spec = self._build_sort_spec(list_params, collection, entity_metadata)
            query_body["sort"] = sort_spec

            res = await es.search(index=collection, body=query_body)
            hits = res.get("hits", {}).get("hits", [])
            results = [{**hit["_source"], "id": self._normalize_id(hit["_id"])} for hit in hits]
            
            # Extract total count from search response
            total_count = res.get("hits", {}).get("total", {}).get("value", 0)
            
            return results, warnings, total_count
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_list"
            )


    async def get_by_id(self, collection: str, doc_id: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Get a document by ID."""
        es = self._get_client()
        try:
            warnings = []
            # Check unique constraints if provided
            if unique_constraints:
                missing_indexes = await self._check_unique_indexes(collection, unique_constraints)
                if missing_indexes:
                    warnings.extend(missing_indexes)
            
            # Try the ID as-is first, then try to find by normalized ID if that fails
            try:
                res = await es.get(index=collection, id=doc_id)
            except ESNotFoundError:
                # If direct lookup fails, try to find document by searching for normalized ID
                # This handles case where we receive lowercase ID but ES has mixed case
                search_res = await es.search(
                    index=collection,
                    body={
                        "query": {"match_all": {}},
                        "size": 10000  # Get all documents to search through
                    }
                )
                
                for hit in search_res.get("hits", {}).get("hits", []):
                    if self._normalize_id(hit["_id"]) == self._normalize_id(doc_id):
                        # Handle case where hit _source might be None
                        hit_source = hit.get("_source") or {}
                        res = {"_source": hit_source, "_id": hit["_id"]}
                        break
                else:
                    raise NotFoundError(collection, doc_id)
            
            # Handle case where _source might be None
            source_data = res.get("_source") or {}
            result = {**source_data, "id": self._normalize_id(res["_id"])}
            return result, warnings
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_by_id"
            )


    async def close(self) -> None:
        """Close the database connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logging.info("Elasticsearch: Connection closed")

    async def collection_exists(self, collection: str) -> bool:
        """Check if a collection exists."""
        es = self._get_client()
        try:
            return bool(await es.indices.exists(index=collection))
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="collection_exists"
            )

    async def create_collection(self, collection: str, indexes: List[Dict[str, Any]]) -> bool:
        """Create a collection - relies on index template for proper mapping."""
        es = self._get_client()
        try:
            # Check if index already exists
            if await es.indices.exists(index=collection):
                return True
                
            # Don't create empty index - let template apply on first document write
            # This ensures our cluster-level template with .raw subfields takes effect
            # 
            # If there are unique constraint indexes to create, we'll handle them 
            # when the first document is written and the template auto-creates the index
            
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="create_collection"
            )

    def _build_query_filter(self, list_params, entity_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build Elasticsearch query from ListParams with field-type awareness."""
        if not list_params or not list_params.filters:
            return {"match_all": {}}
        
        must_clauses = []
        for field, value in list_params.filters.items():
            if isinstance(value, dict) and ('$gte' in value or '$lte' in value or '$gt' in value or '$lt' in value):
                # Comparison filter - convert MongoDB-style to Elasticsearch range query
                range_query = {}
                if '$gte' in value:
                    range_query['gte'] = value['$gte']
                if '$lte' in value:
                    range_query['lte'] = value['$lte']
                if '$gt' in value:
                    range_query['gt'] = value['$gt']
                if '$lt' in value:
                    range_query['lt'] = value['$lt']
                
                # For date/numeric fields, add null exclusion and date normalization
                field_type = self._get_field_type(field, entity_metadata)
                if field_type in ['Date', 'Datetime', 'Integer', 'Currency', 'Float']:
                    # Convert date strings to proper format for date comparison
                    if field_type in ['Date', 'Datetime']:
                        for op in ['gte', 'lte', 'gt', 'lt']:
                            if op in range_query and isinstance(range_query[op], str):
                                # Normalize date string format for ES
                                date_str = range_query[op].strip()
                                if 'T' not in date_str and ' ' not in date_str:
                                    # Add time component if just date (YYYY-MM-DD)
                                    if len(date_str) == 10 and date_str.count('-') == 2:
                                        date_str = f"{date_str}T00:00:00"
                                range_query[op] = date_str
                    
                    # Use bool query to combine range and exists clauses
                    must_clauses.append({
                        "bool": {
                            "must": [
                                {"range": {field: range_query}},
                                {"exists": {"field": field}}
                            ]
                        }
                    })
                else:
                    # For other field types, use range query as-is
                    must_clauses.append({"range": {field: range_query}})
            else:
                # Determine matching strategy using metadata service
                from app.metadata import get_entity_metadata, get_proper_entity_name
                entity_name = get_proper_entity_name(collection)
                entity_meta = get_entity_metadata(entity_name) 
                
                use_partial = False
                if entity_meta:
                    field_info = entity_meta.get_field_info(field)
                    if field_info and field_info.type == 'String' and not entity_meta.is_enum_field(field):
                        use_partial = True
                
                if use_partial:
                    # String fields without enum: partial match with wildcard
                    must_clauses.append({
                        "wildcard": {
                            field: f"*{value}*"
                        }
                    })
                else:
                    # Non-string fields, enums, etc.: exact match
                    # Use .raw for string fields only
                    filter_field = self._get_internal_field_name(field, collection)
                    must_clauses.append({"term": {filter_field: value}})
        
        if must_clauses:
            return {"bool": {"must": must_clauses}}
        else:
            return {"match_all": {}}

    def _build_sort_spec(self, list_params, collection: str, entity_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Build Elasticsearch sort specification from ListParams using metadata."""
        if not list_params or not list_params.sort_fields:
            # Default sort by id field
            default_field = self._get_default_sort_field(entity_metadata)
            return [{default_field: {"order": "asc"}}]
        
        sort_spec = []
        for field, order in list_params.sort_fields:
            actual_field = self._map_sort_field(field, entity_metadata)
                
            # Configure case sensitivity for text fields
            sort_config = {"order": order}
            from app.metadata import get_entity_metadata, get_proper_entity_name
            entity_name = get_proper_entity_name(collection)
            entity_meta = get_entity_metadata(entity_name)
            
            is_string_non_enum = False
            if entity_meta:
                field_info = entity_meta.get_field_info(actual_field)
                if field_info and field_info.type == 'String' and not entity_meta.is_enum_field(actual_field):
                    is_string_non_enum = True
                    
            if not self.case_sensitive_sorting and is_string_non_enum:
                # For case-insensitive sorting on non-enum string fields, always use .raw for scripts
                script_field = self._get_internal_field_name(actual_field, collection)
                sort_config = {
                    "_script": {
                        "type": "string",
                        "script": {
                            "lang": "painless",
                            "source": f"doc.containsKey('{script_field}') && doc['{script_field}'].size() > 0 ? doc['{script_field}'].value.toLowerCase() : ''"
                        },
                        "order": order
                    }
                }
                sort_spec.append(sort_config)
            else:
                # For non-scripted sorting, use .raw for string fields only
                sort_field = self._get_internal_field_name(actual_field, collection)
                
                # For date fields, add missing value handling to prevent epoch dates
                if entity_meta:
                    field_info = entity_meta.get_field_info(actual_field)
                    if field_info and field_info.type in ['Date', 'Datetime']:
                        sort_config["missing"] = "_last"  # Put missing dates at end
                
                sort_spec.append({sort_field: sort_config})
        
        return sort_spec
    



    async def delete_collection(self, collection: str) -> bool:
        """Delete a collection."""
        es = self._get_client()
        try:
            if await es.indices.exists(index=collection):
                await es.indices.delete(index=collection)
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="delete_collection"
            )

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document."""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                return False
            await es.delete(index=collection, id=doc_id)
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="delete_document"
            )

    async def remove_entity(self, collection: str) -> bool:
        """Remove/drop entire entity index."""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                return True  # Already doesn't exist
            await es.indices.delete(index=collection)
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="remove_entity"
            )

    async def list_collections(self) -> List[str]:
        """List all collections."""
        es = self._get_client()
        try:
            indices = await es.indices.get_alias()
            return list(indices.keys())
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity="collections",
                operation="list_collections"
            )

    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes for a collection."""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                return []
            
            mapping = await es.indices.get_mapping(index=collection)
            properties = mapping[collection]['mappings'].get('properties', {})
            standardized_indexes = []
            
            for field_name in properties.keys():
                # In Elasticsearch, each field is essentially an index
                # System fields typically start with underscore
                is_system = field_name.startswith('_')
                
                standardized_indexes.append({
                    'name': field_name,
                    'fields': [field_name],
                    'unique': False,  # Elasticsearch doesn't have unique constraints like MongoDB
                    'system': is_system
                })
            
            return standardized_indexes
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="list_indexes"
            )

    async def find_all(self, collection: str) -> List[Dict[str, Any]]:
        """Get all documents from a collection."""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                return []
                
            res = await es.search(index=collection, query={"match_all": {}})
            hits = res.get("hits", {}).get("hits", [])
            return [{**hit["_source"], "id": self._normalize_id(hit["_id"])} for hit in hits]
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="find_all"
            )

    async def _ensure_collection_exists(self, collection: str, indexes: List[Dict[str, Any]]) -> None:
        """Ensure a collection exists with required indexes."""
        if not await self.collection_exists(collection):
            await self.create_collection(collection, indexes)

    async def create_index(self, collection: str, fields: List[str], unique: bool = False) -> None:
        """Create an index on a collection."""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                await self.create_collection(collection, [{"fields": fields, "unique": unique}])
                return
                
            # Update mappings for existing index
            properties = {field: {"type": "keyword", "index": True} for field in fields}
            await es.indices.put_mapping(
                index=collection,
                properties=properties
            )
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="create_index"
            )

    async def delete_index(self, collection: str, fields: List[str]) -> None:
        """Delete an index from a collection."""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                return
                
            # Get current mappings
            mapping = await es.indices.get_mapping(index=collection)
            properties = mapping[collection]['mappings'].get('properties', {})
            
            # Remove fields from mappings
            for field in fields:
                properties.pop(field, None)
                
            # Update mappings
            await es.indices.put_mapping(
                index=collection,
                properties=properties
            )
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="delete_index"
            )

    async def exists(self, collection: str, doc_id: str) -> bool:
        """Check if a document exists."""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                return False
                
            response = await es.exists(index=collection, id=doc_id)
            return bool(response)
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="exists"
            )

    async def supports_native_indexes(self) -> bool:
        """Elasticsearch does not support native unique indexes"""
        return False
    
    async def document_exists_with_field_value(self, collection: str, field: str, value: Any, exclude_id: Optional[str] = None) -> bool:
        """Check if a document exists with the given field value"""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                return False
            
            # Check field type to determine correct query field
            query_field = field
            try:
                mapping = await es.indices.get_mapping(index=collection)
                existing_properties = mapping[collection]['mappings'].get('properties', {})
                
                if field in existing_properties:
                    field_type = existing_properties[field].get('type', 'text')
                    if field_type == 'text':
                        # For text fields, we need to use the .raw subfield for exact matching
                        if 'fields' in existing_properties[field] and 'raw' in existing_properties[field]['fields']:
                            query_field = f"{field}.raw"
                        else:
                            # Fall back to match query for text fields without raw subfield
                            query = {"match": {field: value}}
                            if exclude_id:
                                query = {
                                    "bool": {
                                        "must": [{"match": {field: value}}],
                                        "must_not": [{"term": {"_id": exclude_id}}]
                                    }
                                }
                            result = await es.search(
                                index=collection,
                                body={"query": query, "size": 1}
                            )
                            return result['hits']['total']['value'] > 0
            except Exception:
                # If we can't get mapping info, use the original field name
                pass
            
            # Build query to search for field value using term query (exact match)
            query = {"term": {query_field: value}}
            
            # Exclude specific document ID if provided
            if exclude_id:
                query = {
                    "bool": {
                        "must": [{"term": {query_field: value}}],
                        "must_not": [{"term": {"_id": exclude_id}}]
                    }
                }
            
            result = await es.search(
                index=collection,
                body={"query": query, "size": 1}
            )
            
            return result['hits']['total']['value'] > 0
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="document_exists_with_field_value"
            )
    
    async def create_single_field_index(self, collection: str, field: str, index_name: str) -> None:
        """Create a single field index for synthetic index support"""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                # Create collection with this field mapping
                await self.create_collection(collection, [{"fields": [field], "unique": False}])
                return
                
            # Check if field already exists and what type it is
            try:
                mapping = await es.indices.get_mapping(index=collection)
                existing_properties = mapping[collection]['mappings'].get('properties', {})
                
                if field in existing_properties:
                    # Field already exists - check if it's suitable for exact matching
                    existing_type = existing_properties[field].get('type', 'text')
                    if existing_type == 'text':
                        # For text fields, we need to use the .raw subfield if it exists
                        # or create a multi-field mapping
                        if 'fields' not in existing_properties[field]:
                            # Add raw subfield to existing text field
                            properties = {
                                field: {
                                    "type": "text",
                                    "fields": {
                                        "raw": {
                                            "type": "keyword",
                                            "ignore_above": 256
                                        }
                                    }
                                }
                            }
                            await es.indices.put_mapping(
                                index=collection,
                                properties=properties
                            )
                        # Field is already suitable or has been made suitable
                        return
                    elif existing_type == 'keyword':
                        # Already perfect for exact matching
                        return
                
                # Field doesn't exist - add it as keyword
                properties = {field: {"type": "keyword"}}
                await es.indices.put_mapping(
                    index=collection,
                    properties=properties
                )
                
            except Exception as mapping_error:
                # If we can't get or update mapping, log warning but continue
                logging.warning(f"Failed to update mapping for field '{field}': {str(mapping_error)}")
            
        except Exception as e:
            # Log warning but don't fail - index creation is optional for performance
            logging.warning(f"Failed to create synthetic index '{index_name}' on field '{field}': {str(e)}")
    
    # ES-specific synthetic index methods
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
        import hashlib
        combined = "|".join(values)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def prepare_document_for_save(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None, entity_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Prepare document for save by converting datetime fields and adding synthetic hash fields"""
        
        # Step 1: Convert datetime fields based on metadata
        processed_data = self._process_datetime_fields_for_save(data, entity_metadata)
        
        # Step 2: Add synthetic hash fields for unique constraints (ES always needs them)
        if unique_constraints:
            processed_data = self._add_synthetic_hash_fields(processed_data, unique_constraints)
            
        return processed_data
    
    async def validate_unique_constraints_before_save(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> None:
        """Validate unique constraints before saving using synthetic indexes"""
        if unique_constraints:
            await self._validate_synthetic_constraints(collection, data, unique_constraints)

    async def save_document(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None, entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Save a document to the database with synthetic index support."""
        self._ensure_initialized()
        
        try:
            warnings = []
            
            # Prepare document with synthetic hash fields
            prepared_data = await self.prepare_document_for_save(collection, data, unique_constraints, entity_metadata)
            
            # Validate unique constraints before save
            await self.validate_unique_constraints_before_save(collection, prepared_data, unique_constraints)
            
            # Perform the actual save
            es = self._get_client()
            doc_id = prepared_data.get('id')
            
            # Let ES auto-create the index on first write - template will apply automatically
            # No need to pre-create empty collections
            
            # Handle new documents vs updates
            if not doc_id or (isinstance(doc_id, str) and doc_id.strip() == ""):
                # New document - let Elasticsearch auto-generate ID
                save_data = prepared_data.copy()
                save_data.pop('id', None)
                
                result = await es.index(index=collection, body=save_data)
                doc_id_str = result['_id']
            else:
                # Update existing document
                save_data = prepared_data.copy()
                save_data.pop('id', None)
                
                await es.index(index=collection, id=doc_id, body=save_data)
                doc_id_str = str(doc_id)
            
            # Get the saved document
            saved_doc, get_warnings = await self.get_by_id(collection, doc_id_str)
            warnings.extend(get_warnings)
            
            return saved_doc, warnings
            
        except SyntheticDuplicateError as e:
            # Convert synthetic duplicate error to standard DuplicateError
            raise DuplicateError(
                entity=e.collection,
                field=e.field,
                value=e.value
            )
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="save_document"
            )
    
    async def _check_unique_indexes(self, collection: str, unique_constraints: List[List[str]]) -> List[str]:
        """Check if unique indexes exist for the given constraints. Returns list of missing constraint descriptions."""
        if not unique_constraints:
            return []
            
        try:
            # Note: Elasticsearch doesn't have traditional unique constraints like MongoDB
            # In Elasticsearch, uniqueness is typically enforced at the application level
            # For now, we'll just warn that Elasticsearch doesn't support unique constraints natively
            
            missing_constraints = []
            for constraint_fields in unique_constraints:
                constraint_desc = " + ".join(constraint_fields) if len(constraint_fields) > 1 else constraint_fields[0]
                missing_constraints.append(f"Missing unique constraint for {constraint_desc} - Elasticsearch doesn't support unique indexes")
            
            return missing_constraints
            
        except Exception as e:
            # Return empty list on error - Factory layer will handle notification
            return []