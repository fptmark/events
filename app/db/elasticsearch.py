import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from elastic_transport import ObjectApiResponse
from elasticsearch import AsyncElasticsearch, NotFoundError

from .base import DatabaseInterface, T
from ..errors import DatabaseError, ValidationError, ValidationFailure


class ElasticsearchDatabase(DatabaseInterface):
    """
    Elasticsearch implementation of DatabaseInterface.
    
    Wraps AsyncElasticsearch client and provides the standard database interface.
    """

    def __init__(self):
        self._client: Optional[AsyncElasticsearch] = None
        self._url: str = ""
        self._dbname: str = ""

    @property
    def id_field(self) -> str:
        """Elasticsearch uses '_id' as the document ID field"""
        return "_id"

    async def init(self, connection_str: str, database_name: str) -> None:
        """
        Initialize Elasticsearch connection.
        
        Args:
            connection_str: Elasticsearch URL
            database_name: Database name (used for logging, ES doesn't have databases)
        """
        if self._client is not None:
            logging.info("Elasticsearch already initialised – re‑using client")
            return

        self._url, self._dbname = connection_str, database_name
        client = AsyncElasticsearch(hosts=[connection_str])

        # Fail fast if ES is down
        try:
            info = await client.info()
            logging.info("Connected to Elasticsearch %s", info["version"]["number"])
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to connect to Elasticsearch: {str(e)}",
                entity="connection",
                operation="init"
            )

        self._client = client

    def _get_client(self) -> AsyncElasticsearch:
        """
        Get the AsyncElasticsearch client instance.
        
        Returns:
            AsyncElasticsearch client
            
        Raises:
            RuntimeError: If init() hasn't been called
        """
        if self._client is None:
            raise RuntimeError("ElasticsearchDatabase.init() has not been awaited")
        return self._client

    async def find_all(self, collection: str, model_cls: Type[T]) -> List[T]:
        """Find all documents in an Elasticsearch index"""
        es = self._get_client()

        if not await es.indices.exists(index=collection):
            return []

        try:
            res = await es.search(index=collection, query={"match_all": {}})
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="find_all"
            )

        hits = res.get("hits", {}).get("hits", [])
        validated_docs = []
        
        for hit in hits:
            try:
                doc_data = {**hit["_source"], self.id_field: hit[self.id_field]}
                validated_docs.append(self.validate_document(doc_data, model_cls))
            except ValidationError as e:
                logging.error(f"Validation failed for document {hit[self.id_field]}: {e.message}")
                # Skip invalid documents but continue processing
                continue
                
        return validated_docs

    async def get_by_id(self, collection: str, doc_id: str, model_cls: Type[T]) -> Optional[T]:
        """Get a document by ID from Elasticsearch"""
        es = self._get_client()
        logging.info(f"ES get_by_id called for {collection}/{doc_id}")
        try:
            res = await es.get(index=collection, id=doc_id)
            logging.info(f"ES get_by_id success: {res}")
            doc_data = {**res["_source"], self.id_field: res["_id"]}
            return self.validate_document(doc_data, model_cls)
        except NotFoundError as e:
            logging.error(f"ES NotFoundError in get_by_id for {collection}/{doc_id}: {str(e)}")
            return None
        except ValidationError as e:
            logging.error(f"ValidationError in get_by_id for {collection}/{doc_id}: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in get_by_id for {collection}/{doc_id}: {str(e)}")
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_by_id"
            )

    async def save_document(self, collection: str, doc_id: Optional[str],
                          data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> ObjectApiResponse[Any]:
        """Save a document to Elasticsearch"""
        es = self._get_client()

        try:
            # Check unique constraints if provided
            if unique_constraints:
                await self.check_unique_constraints(collection, unique_constraints, data, doc_id)

            # Save the document directly
            return (await es.index(index=collection, id=doc_id, document=data)
                    if doc_id else
                    await es.index(index=collection, document=data))
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="save"
            )

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from Elasticsearch"""
        es = self._get_client()
        try:
            if not await es.exists(index=collection, id=doc_id):
                return False
            await es.delete(index=collection, id=doc_id)
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="delete"
            )

    async def exists(self, collection: str, doc_id: str) -> bool:
        """Check if a document exists in Elasticsearch"""
        es = self._get_client()
        try:
            result = await es.exists(index=collection, id=doc_id)
            return bool(result)
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="exists"
            )

    async def check_unique_constraints(self, collection: str, constraints: List[List[str]], 
                                     data: Dict[str, Any], exclude_id: Optional[str] = None) -> List[str]:
        """
        Check uniqueness constraints using Elasticsearch bool queries.
        
        Returns list of field names that have conflicts.
        """
        es = self._get_client()
        conflicting_fields = []
        missing_constraints = []
        
        try:
            # First check if the index exists
            if not await es.indices.exists(index=collection):
                # If index doesn't exist, all unique constraints are considered missing
                missing_constraints = [
                    f"unique constraint on {fields[0]}" if len(fields) == 1 
                    else f"composite unique constraint on ({', '.join(fields)})"
                    for fields in constraints
                ]
                raise ValidationError(
                    message=f"{collection.title()} operation failed: Required constraints missing: {'; '.join(missing_constraints)}",
                    entity=collection,
                    invalid_fields=[
                        ValidationFailure(
                            field="constraints",
                            message="Missing required indexes",
                            value='; '.join(missing_constraints)
                        )
                    ]
                )

            # Check each unique constraint set
            for unique_fields in constraints:
                # Build terms for all fields in this unique constraint
                must_terms = []
                for field in unique_fields:
                    if field not in data:
                        # Skip this constraint if we don't have all fields
                        break
                    must_terms.append({"term": {field: data[field]}})
                
                if len(must_terms) != len(unique_fields):
                    # Skip if we didn't get all fields for this constraint
                    continue

                # Build the ES query
                query = {
                    "bool": {
                        "must": must_terms
                    }
                }

                # Add exclusion for updates
                if exclude_id:
                    query["bool"]["must_not"] = [
                        {"term": {self.id_field: exclude_id}}
                    ]

                try:
                    # Execute targeted search
                    res = await es.search(
                        index=collection,
                        query=query,
                        size=1  # We only need to know if any exist
                    )
                    
                    # Check if any documents matched
                    if res.get("hits", {}).get("total", {}).get("value", 0) > 0:
                        # Add the conflicting fields to our list
                        conflicting_fields.extend(unique_fields)
                        
                except Exception as search_error:
                    logging.error(f"Error checking uniqueness for {unique_fields}: {search_error}")
                    # For other errors, continue checking remaining constraints
                    continue
                    
        except ValidationError:
            # Re-raise validation errors (like missing constraints)
            raise
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to check unique constraints: {str(e)}",
                entity=collection,
                operation="check_unique_constraints"
            )
            
        return conflicting_fields

    async def close(self) -> None:
        """Close the Elasticsearch connection"""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logging.info("Elasticsearch connection closed")

    async def list_collections(self) -> List[str]:
        """List all indices in Elasticsearch"""
        es = self._get_client()
        try:
            result = await es.indices.get(index="*")
            return list(result.keys())
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to list collections: {str(e)}",
                entity="indices",
                operation="list_collections"
            )

    async def create_collection(self, collection: str, **kwargs) -> bool:
        """Create an index in Elasticsearch with proper field mappings"""
        es = self._get_client()
        try:
            if await es.indices.exists(index=collection):
                return False  # Already exists
            
            # Extract ES-specific settings from kwargs
            settings = kwargs.get('settings', {})
            mappings = kwargs.get('mappings', {})
            
            # If no mappings provided, create a default mapping that ensures
            # all string fields are both searchable text and exact-match keywords
            if not mappings:
                mappings = {
                    "dynamic_templates": [
                        {
                            "strings": {
                                "match_mapping_type": "string",
                                "mapping": {
                                    "type": "keyword",  # For exact matching (needed for unique constraints)
                                    "fields": {
                                        "text": {  # Also add text mapping for full-text search
                                            "type": "text"
                                        }
                                    }
                                }
                            }
                        }
                    ]
                }
            
            body = {
                "settings": settings,
                "mappings": mappings
            }
            
            await es.indices.create(index=collection, body=body)
            logging.info(f"Created index: {collection}")
            return True
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create collection '{collection}': {str(e)}",
                entity=collection,
                operation="create_collection"
            )

    async def delete_collection(self, collection: str) -> bool:
        """Delete an index from Elasticsearch"""
        es = self._get_client()
        try:
            if not await es.indices.exists(index=collection):
                return False  # Doesn't exist
            
            await es.indices.delete(index=collection)
            logging.info(f"Deleted index: {collection}")
            return True
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete collection '{collection}': {str(e)}",
                entity=collection,
                operation="delete_collection"
            )

    async def collection_exists(self, collection: str) -> bool:
        """Check if an index exists in Elasticsearch"""
        es = self._get_client()
        try:
            result = await es.indices.exists(index=collection)
            return bool(result)
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to check if collection '{collection}' exists: {str(e)}",
                entity=collection,
                operation="collection_exists"
            )

    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes for a specific Elasticsearch index"""
        es = self._get_client()
        try:
            # Get index mapping to see what fields are indexed
            mapping_response = await es.indices.get_mapping(index=collection)
            
            indexes = []
            if collection in mapping_response:
                mappings = mapping_response[collection].get('mappings', {})
                properties = mappings.get('properties', {})
                
                # Add primary ID index (always exists)
                indexes.append({
                    'name': '_id_',
                    'fields': [self.id_field],
                    'unique': True,
                    'system': True
                })
                
                # Look for unique constraints in field mappings
                for field_name, field_def in properties.items():
                    # In ES, we would typically use term-level queries for uniqueness
                    # but there's no built-in unique constraint, so we list searchable fields
                    if field_def.get('type') in ['keyword', 'text']:
                        indexes.append({
                            'name': f'{field_name}_search',
                            'fields': [field_name],
                            'unique': False,
                            'system': False
                        })
            
            return indexes
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to list indexes for collection '{collection}': {str(e)}",
                entity=collection,
                operation="list_indexes"
            )

    async def create_index(self, collection: str, fields: List[str], unique: bool = False, **kwargs) -> bool:
        """
        Create an index in Elasticsearch.
        Note: ES doesn't have traditional indexes like SQL, but we can ensure proper mappings.
        """
        es = self._get_client()
        try:
            # Check if collection exists
            if not await es.indices.exists(index=collection):
                return False  # Collection doesn't exist
            
            # Get current mapping
            mapping_response = await es.indices.get_mapping(index=collection)
            current_mapping = mapping_response.get(collection, {}).get('mappings', {})
            current_properties = current_mapping.get('properties', {})
            
            # Prepare new field mappings
            new_properties = {}
            for field in fields:
                if field not in current_properties:
                    # Add as keyword for exact matching (needed for uniqueness checks)
                    new_properties[field] = {
                        "type": "keyword"
                    }
            
            if new_properties:
                # Update mapping with new fields
                await es.indices.put_mapping(
                    index=collection,
                    body={"properties": new_properties}
                )
                logging.info(f"Added field mappings for {fields} in collection {collection}")
                return True
            
            return False  # No new fields to add
            
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create index on {fields} for collection '{collection}': {str(e)}",
                entity=collection,
                operation="create_index"
            )

    async def delete_index(self, collection: str, index_name: str) -> bool:
        """
        Delete an index in Elasticsearch.
        Note: ES doesn't have traditional index deletion, this is more about field removal.
        """
        # In Elasticsearch, we typically don't delete individual field mappings
        # as it's not supported. This would require reindexing.
        logging.warning(f"Index deletion not supported in Elasticsearch for index '{index_name}' in collection '{collection}'")
        return False

    async def _ensure_collection_exists(self, collection: str) -> None:
        """Ensure an Elasticsearch index exists, creating it if necessary"""
        if not await self.collection_exists(collection):
            logging.info(f"Creating collection '{collection}'")
            await self.create_collection(collection)

    async def _create_required_indexes(self, collection: str, required_indexes: List[Dict[str, Any]]) -> None:
        """Create required indexes for an Elasticsearch index"""
        # Get existing indexes
        existing_indexes = await self.list_indexes(collection)
        existing_index_names = {idx['name'] for idx in existing_indexes}
        
        # Create missing indexes
        for required_idx in required_indexes:
            if required_idx['name'] not in existing_index_names:
                try:
                    created = await self.create_index(
                        collection, 
                        required_idx['fields'],
                        unique=required_idx['unique']
                    )
                    if created:
                        fields_str = " + ".join(required_idx['fields'])
                        logging.info(f"Created index '{required_idx['name']}' on {fields_str}")
                    else:
                        logging.info(f"Index '{required_idx['name']}' already exists or couldn't be created")
                except Exception as e:
                    logging.error(f"Failed to create index '{required_idx['name']}': {str(e)}")
            else:
                logging.info(f"Index '{required_idx['name']}' already exists")