"""
Elasticsearch implementation of the database interface.
Each manager is implemented as a separate class for clean separation.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from elasticsearch import AsyncElasticsearch

from .base import DatabaseInterface
from .core_manager import CoreManager
from .document_manager import DocumentManager
from .entity_manager import EntityManager
from .index_manager import IndexManager
from ..errors import DatabaseError
from app.services.notification import duplicate_warning, validation_warning, not_found_warning
from app.services.metadata import MetadataService


class ElasticsearchCore(CoreManager):
    """Elasticsearch implementation of core operations"""
    
    def __init__(self, parent: 'ElasticsearchDatabase'):
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

        try:
            self._client = AsyncElasticsearch([connection_str])
            self._database_name = database_name
            
            # Test connection
            await self._client.ping()
            self.parent._initialized = True
            logging.info(f"ElasticsearchDatabase: Connected to {database_name}")
            
            # Create index template for .raw subfields on all new indices
            await self._ensure_index_template()
            
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to connect to Elasticsearch: {str(e)}",
                entity="connection",
                operation="init"
            )
    
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
        try:
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
        except Exception as e:
            logging.warning(f"Failed to create index template: {e}")
            # Don't fail initialization if template creation fails


class ElasticsearchDocuments(DocumentManager):
    """Elasticsearch implementation of document operations"""
    
    def __init__(self, parent: 'ElasticsearchDatabase'):
        self.parent = parent
    
    
    async def get_all(
        self, 
        entity_type: str, 
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25,
        process_fks: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated list of documents"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        try:
            if not await es.indices.exists(index=entity_type):
                return [], 0
            
            # Build query
            query_body = {
                "from": (page - 1) * pageSize,
                "size": pageSize,
                "query": self._build_query_filter(filter, entity_type)
            }
            
            # Add sorting
            sort_spec = self._build_sort_spec(sort, entity_type)
            if sort_spec:
                query_body["sort"] = sort_spec
            
            # Execute query
            response = await es.search(index=entity_type, body=query_body)
            hits = response.get("hits", {}).get("hits", [])
            
            documents = []
            for hit in hits:
                doc = self._normalize_document(hit["_source"])
                documents.append(doc)
            
            total_count = response.get("hits", {}).get("total", {}).get("value", 0)
            
            return documents, total_count
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="get_all"
            )
    
    async def get(
        self, 
        id: str,
        entity_type: str
    ) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        try:
            index = entity_type
            
            if not await es.indices.exists(index=index):
                not_found_warning(f"Index does not exist", entity=entity_type, entity_id=id)
                return {}, 0
            
            response = await es.get(index=index, id=id)
            doc = self._normalize_document(response["_source"])
            
            # Note: FK processing and view_spec handling done in model layer
            # Database returns raw document data only
            return doc, 1
            
        except Exception as e:
            if "not found" in str(e).lower():
                not_found_warning(f"Document not found", entity=entity_type, entity_id=id)
                return {}, 0
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="get"
            )
    
    async def _validate_document_exists_for_update(self, entity_type: str, id: str) -> bool:
        """Validate that document exists for update operations"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        try:
            index = entity_type
            
            if not await es.indices.exists(index=index):
                from app.services.notification import not_found_warning
                not_found_warning(f"Index does not exist", entity=entity_type, entity_id=id)
                return False
            
            await es.get(index=index, id=id)
            return True
            
        except Exception:
            from app.services.notification import not_found_warning
            not_found_warning(f"Document not found for update", entity=entity_type, entity_id=id)
            return False
    
    async def _create_document(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in Elasticsearch. If data contains 'id', use it as _id, otherwise auto-generate."""
        es = self.parent.core.get_connection()
        
        try:
            index = entity_type
            create_data = data.copy()
            
            # If data contains 'id', use it as Elasticsearch _id
            if 'id' in create_data:
                doc_id = create_data.pop('id')
                response = await es.index(index=index, id=doc_id, body=create_data)
                saved_doc = create_data.copy()
                saved_doc["_id"] = doc_id
            else:
                # Auto-generate ID
                response = await es.index(index=index, body=create_data)
                saved_doc = create_data.copy()
                saved_doc["_id"] = response["_id"]
            
            return saved_doc
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="create"
            )

    async def _update_document(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing document in Elasticsearch. Extracts id from data['id']."""
        es = self.parent.core.get_connection()
        
        try:
            index = entity_type
            id = data['id']  # Extract id from data
            
            # Create update data without 'id' field
            update_data = data.copy()
            del update_data['id']
            
            await es.index(index=index, id=id, body=update_data)
            saved_doc = update_data.copy()
            saved_doc["_id"] = id
            
            return saved_doc
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="update"
            )
    
    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance"""
        return self.parent.core
    
    async def delete(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID after retrieving it"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        try:
            index = entity_type
            
            if not await es.indices.exists(index=index):
                return {}, 0
            
            # First get the document before deleting
            try:
                get_response = await es.get(index=index, id=id)
                doc_to_delete = self._normalize_document(get_response["_source"])
            except Exception as e:
                if "not found" in str(e).lower():
                    not_found_warning(f"Document not found for deletion", entity=entity_type, entity_id=id)
                    return {}, 0
                raise
            
            # Now delete the document
            delete_response = await es.delete(index=index, id=id)
            record_count = 1 if delete_response.get("result") == "deleted" else 0
            
            return doc_to_delete, record_count
            
        except Exception as e:
            if "not found" in str(e).lower():
                return {}, 0
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="delete"
            )
    
    def _build_query_filter(self, filters: Optional[Dict[str, Any]], entity_type: str) -> Dict[str, Any]:
        """Build Elasticsearch query from filter conditions"""
        if not filters:
            return {"match_all": {}}
        
        must_clauses = []
        for field, value in filters.items():
            if isinstance(value, dict) and any(op in value for op in ['$gte', '$lte', '$gt', '$lt']):
                # Range query
                range_query = {}
                for op, val in value.items():
                    es_op = op.replace('$', '')  # $gte -> gte
                    range_query[es_op] = val
                must_clauses.append({"range": {field: range_query}})
            else:
                # Exact match
                must_clauses.append({"term": {field: value}})
        
        return {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
    
    def _build_sort_spec(self, sort_fields: Optional[List[Tuple[str, str]]], entity_type: str) -> List[Dict[str, Any]]:
        """Build Elasticsearch sort specification"""
        if not sort_fields:
            default_sort_field = self.parent.core._get_default_sort_field(entity_type)
            return [{default_sort_field: {"order": "asc"}}]  
        
        sort_spec = []
        for field, direction in sort_fields:
            sort_spec.append({field: {"order": direction}})
        
        return sort_spec
    
    def _prepare_datetime_fields(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for Elasticsearch storage (as ISO strings)"""
        from datetime import datetime
        
        fields_meta = MetadataService.fields(entity_type)
        data_copy = data.copy()
        
        for field_name, field_meta in fields_meta.items():
            if field_name in data_copy and field_meta.get('type') == 'DateTime':
                value = data_copy[field_name]
                if isinstance(value, datetime):
                    # Convert datetime to ISO string for ES storage
                    data_copy[field_name] = value.isoformat()
        
        return data_copy
    
    async def _validate_unique_constraints(
        self, 
        entity_type: str, 
        data: Dict[str, Any], 
        unique_constraints: List[List[str]], 
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints (Elasticsearch synthetic implementation)"""
        
        # Get unique constraints from metadata if not provided
        if not unique_constraints:
            metadata = MetadataService.get(entity_type) 
            if metadata:
                unique_constraints = metadata.get('unique_constraints', [])
        
        if not unique_constraints:
            return True
            
        es = self.parent.core.get_connection()
        index = entity_type
        
        if not await es.indices.exists(index=index):
            return True  # No existing docs to check against
            
        for constraint_fields in unique_constraints:
            # Build query to check for existing documents with same field values
            must_clauses = []
            for field in constraint_fields:
                if field in data and data[field] is not None:
                    # Use .raw field for exact string matching if it's a text field
                    metadata = MetadataService.get(entity_type)
                    field_type = metadata.get('fields', {}).get(field, {}).get('type', 'String') if metadata else 'String'
                    
                    if field_type == 'String':
                        # Use .raw subfield for exact matching on strings
                        must_clauses.append({"term": {f"{field}.raw": data[field]}})
                    else:
                        # Use direct field for non-string types
                        must_clauses.append({"term": {field: data[field]}})
            
            if not must_clauses:
                continue
                
            # Exclude current document if updating
            query = {"bool": {"must": must_clauses}}
            if exclude_id:
                query["bool"]["must_not"] = [{"term": {"_id": exclude_id}}]
            
            response = await es.search(
                index=index,
                body={"query": query, "size": 1}
            )
            
            if response.get("hits", {}).get("total", {}).get("value", 0) > 0:
                # Use first field in constraint (matches MongoDB pattern)
                duplicate_field = constraint_fields[0]
                from app.errors import DuplicateConstraintError
                raise DuplicateConstraintError(
                    message=f"Duplicate value for field '{duplicate_field}'",
                    entity=entity_type,
                    field=duplicate_field,
                    entity_id=exclude_id or "new"
                )
        
        return True


class ElasticsearchEntities(EntityManager):
    """Elasticsearch implementation of entity operations"""
    
    def __init__(self, parent: 'ElasticsearchDatabase'):
        self.parent = parent
    
    async def exists(self, entity_type: str) -> bool:
        """Check if index exists"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        return await es.indices.exists(index=entity_type)
    
    async def create(self, entity_type: str, unique_constraints: List[List[str]]) -> bool:
        """Create index (Elasticsearch doesn't enforce unique constraints natively)"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        try:
            if await es.indices.exists(index=entity_type):
                return True
                
            await es.indices.create(index=entity_type)
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="create"
            )
    
    async def delete(self, entity_type: str) -> bool:
        """Delete index"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        try:
            if await es.indices.exists(index=entity_type):
                await es.indices.delete(index=entity_type)
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="delete"
            )
    
    async def get_all(self) -> List[str]:
        """Get all index names"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        try:
            response = await es.cat.indices(format="json")
            return [index["index"] for index in response]
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity="",
                operation="list_entities"
            )


class ElasticsearchIndexes(IndexManager):
    """Elasticsearch implementation of index operations (limited functionality)"""
    
    def __init__(self, parent: 'ElasticsearchDatabase'):
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
        
        try:
            # Ensure index exists
            if not await es.indices.exists(index=entity_type):
                await es.indices.create(index=entity_type)
            
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
                index=entity_type,
                properties=properties
            )
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="create_index"
            )
    
    async def get_all(self, entity_type: str) -> List[List[str]]:
        """Get synthetic unique indexes (hash fields) for Elasticsearch"""
        self.parent._ensure_initialized()
        es = self.parent.core.get_connection()
        
        try:
            if not await es.indices.exists(index=entity_type):
                return []
            
            # For Elasticsearch, we look for hash fields that represent unique constraints
            # Hash fields follow pattern: _hash_field1_field2_... for multi-field constraints
            response = await es.indices.get_mapping(index=entity_type)
            mapping = response.get(entity_type, {}).get("mappings", {}).get("properties", {})
            
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
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="list_indexes"
            )
    
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


class ElasticsearchDatabase(DatabaseInterface):
    """Elasticsearch implementation of DatabaseInterface"""
    
    def _create_core_manager(self) -> CoreManager:
        return ElasticsearchCore(self)
    
    def _create_document_manager(self) -> DocumentManager:
        return ElasticsearchDocuments(self)
    
    def _create_entity_manager(self) -> EntityManager:
        return ElasticsearchEntities(self)
    
    def _create_index_manager(self) -> IndexManager:
        return ElasticsearchIndexes(self)
    
    async def supports_native_indexes(self) -> bool:
        """Elasticsearch does not support native unique indexes"""
        return False