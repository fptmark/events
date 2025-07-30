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

    def __init__(self):
        super().__init__()
        self._client: Optional[AsyncElasticsearch] = None
        self._url: str = ""
    
    def _convert_datetime_fields(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime string fields back to datetime objects for Pydantic compatibility."""
        if not document:
            return document
        
        # Known datetime fields that need conversion
        datetime_fields = {'createdAt', 'updatedAt', 'dob'}
        
        doc_copy = document.copy()
        for field_name, value in doc_copy.items():
            if field_name in datetime_fields and isinstance(value, str):
                try:
                    # Parse ISO format datetime strings back to datetime objects
                    if value.endswith('Z'):
                        # Remove Z and add +00:00 for proper parsing
                        value = value[:-1] + '+00:00'
                    doc_copy[field_name] = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    # If parsing fails, leave as string (Pydantic will handle validation)
                    pass
        
        return doc_copy

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
        except Exception as e:
            self._handle_connection_error(e, database_name)

    def _get_client(self) -> AsyncElasticsearch:
        """Get the AsyncElasticsearch client instance."""
        self._ensure_initialized()
        assert self._client is not None, "Client should be initialized after _ensure_initialized()"
        return self._client

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
            results = [self._convert_datetime_fields({**hit["_source"], "id": self._normalize_id(hit["_id"])}) for hit in hits]
            
            # Extract total count from search response
            total_count = res.get("hits", {}).get("total", {}).get("value", 0)
            
            return results, warnings, total_count
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_all"
            )

    async def get_list(self, collection: str, unique_constraints: Optional[List[List[str]]] = None, list_params=None, entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
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
            query_body = {
                "from": (list_params.page - 1) * list_params.page_size,
                "size": list_params.page_size,
                "query": self._build_query_filter(list_params, entity_metadata)
            }
            
            # Always add sorting for consistent pagination
            sort_spec = self._build_sort_spec(list_params)
            query_body["sort"] = sort_spec

            res = await es.search(index=collection, body=query_body)
            hits = res.get("hits", {}).get("hits", [])
            results = [self._convert_datetime_fields({**hit["_source"], "id": self._normalize_id(hit["_id"])}) for hit in hits]
            
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
                        res = {"_source": hit["_source"], "_id": hit["_id"]}
                        break
                else:
                    raise NotFoundError(collection, doc_id)
            
            result = self._convert_datetime_fields({**res["_source"], "id": self._normalize_id(res["_id"])})
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
        """Create a collection with indexes."""
        es = self._get_client()
        try:
            # Create index with mappings
            mappings: Dict[str, Any] = {
                "mappings": {
                    "properties": {}
                }
            }
            
            # Add fields from indexes
            for index in indexes:
                for field in index['fields']:
                    mappings["mappings"]["properties"][field] = {
                        "type": "keyword",
                        "index": True
                    }
            
            # Create index with mappings
            await es.indices.create(index=collection, body=mappings)
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
            if isinstance(value, dict) and ('$gte' in value or '$lte' in value):
                # Range filter - convert MongoDB-style to Elasticsearch range query
                range_query = {}
                if '$gte' in value:
                    range_query['gte'] = value['$gte']
                if '$lte' in value:
                    range_query['lte'] = value['$lte']
                must_clauses.append({"range": {field: range_query}})
            else:
                # Determine matching strategy based on field type
                field_type = self._get_field_type(field, entity_metadata)
                if field_type == 'String':
                    # Text fields: partial match with wildcard on the base field
                    # Since our mappings create fields as keyword type, use the field directly
                    must_clauses.append({
                        "wildcard": {
                            field: f"*{value}*"
                        }
                    })
                else:
                    # Non-text fields (enums, numbers, dates, etc.): exact match
                    # Since our mappings create fields as keyword type, use the field directly
                    must_clauses.append({"term": {field: value}})
        
        if must_clauses:
            return {"bool": {"must": must_clauses}}
        else:
            return {"match_all": {}}

    def _build_sort_spec(self, list_params) -> List[Dict[str, Any]]:
        """Build Elasticsearch sort specification from ListParams."""
        if not list_params:
            # Default sort by createdAt for consistent pagination when no sort specified
            # Note: Never use _id in sort - it requires fielddata which is disabled by default
            return [{"createdAt": {"order": "asc"}}]
        
        if not list_params.sort_field:
            # Default sort by createdAt for consistent pagination when no sort specified
            return [{"createdAt": {"order": "asc"}}]
        
        sort_order = "asc" if list_params.sort_order == "asc" else "desc"
        
        # Map application "id" field to Elasticsearch "_id" field for sorting
        # But _id requires fielddata, so we fall back to createdAt
        if list_params.sort_field == "id":
            # Cannot sort by _id without enabling fielddata, use createdAt instead
            return [{"createdAt": {"order": sort_order}}]
        
        # Since our mappings create fields as keyword type, use the field directly
        return [{list_params.sort_field: {"order": sort_order}}]

    def _get_field_type(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> str:
        """Get field type from entity metadata or default to String."""
        if not entity_metadata:
            return 'String'
        
        field_info = entity_metadata.get('fields', {}).get(field_name, {})
        field_type = field_info.get('type', 'String')
        
        # Check if field has enum values - treat as exact match even if type is String
        if 'enum' in field_info:
            return 'Enum'  # Use exact matching for enum fields
        
        return field_type

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
            return [self._convert_datetime_fields({**hit["_source"], "id": self._normalize_id(hit["_id"])}) for hit in hits]
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
                        # For text fields, we need to use the .keyword subfield for exact matching
                        if 'fields' in existing_properties[field] and 'keyword' in existing_properties[field]['fields']:
                            query_field = f"{field}.keyword"
                        else:
                            # Fall back to match query for text fields without keyword subfield
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
                        # For text fields, we need to use the .keyword subfield if it exists
                        # or create a multi-field mapping
                        if 'fields' not in existing_properties[field]:
                            # Add keyword subfield to existing text field
                            properties = {
                                field: {
                                    "type": "text",
                                    "fields": {
                                        "keyword": {
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
    
    async def save_document(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Save a document to the database with synthetic index support."""
        self._ensure_initialized()
        
        try:
            warnings = []
            
            # Prepare document with synthetic hash fields
            prepared_data = await self.prepare_document_for_save(collection, data, unique_constraints)
            
            # Validate unique constraints before save
            await self.validate_unique_constraints_before_save(collection, prepared_data, unique_constraints)
            
            # Perform the actual save
            es = self._get_client()
            doc_id = prepared_data.get('id')
            
            # Create the collection if it doesn't exist
            if not await es.indices.exists(index=collection):
                await self.create_collection(collection, [])
            
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