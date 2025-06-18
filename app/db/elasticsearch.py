import logging
from typing import Any, Dict, List, Optional, Tuple
from elasticsearch import AsyncElasticsearch, NotFoundError

from .base import DatabaseInterface
from ..errors import DatabaseError

class ElasticsearchDatabase(DatabaseInterface):
    """Elasticsearch implementation of DatabaseInterface."""

    def __init__(self):
        self._client: Optional[AsyncElasticsearch] = None
        self._url: str = ""
        self._dbname: str = ""

    @property
    def id_field(self) -> str:
        """Elasticsearch uses '_id' as the document ID field"""
        return "_id"

    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize Elasticsearch connection."""
        if self._client is not None:
            logging.info("Elasticsearch already initialised – re‑using client")
            return

        self._url, self._dbname = connection_str, database_name
        client = AsyncElasticsearch(hosts=[connection_str])

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
        """Get the AsyncElasticsearch client instance."""
        if self._client is None:
            raise RuntimeError("ElasticsearchDatabase.init() has not been awaited")
        return self._client

    async def get_all(self, collection: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Get all documents from a collection."""
        es = self._get_client()

        if not await es.indices.exists(index=collection):
            return [], []

        try:
            warnings = []
            # Check unique constraints if provided
            if unique_constraints:
                missing_indexes = await self._check_unique_indexes(collection, unique_constraints)
                if missing_indexes:
                    warnings.extend(missing_indexes)
            
            res = await es.search(index=collection, query={"match_all": {}})
            hits = res.get("hits", {}).get("hits", [])
            results = [{**hit["_source"], self.id_field: hit[self.id_field]} for hit in hits]
            return results, warnings
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_all"
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
                    logging.warning(f"Missing unique indexes for {collection}: {missing_indexes}")
            
            res = await es.get(index=collection, id=doc_id)
            result = {**res["_source"], self.id_field: res["_id"]}
            return result, warnings
        except NotFoundError:
            raise DatabaseError(
                message=f"Document not found: {doc_id}",
                entity=collection,
                operation="get_by_id"
            )
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_by_id"
            )

    async def save_document(self, collection: str, doc_id: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Save a document to the database."""
        es = self._get_client()
        try:
            warnings = []
            # Check unique constraints if provided
            if unique_constraints:
                missing_indexes = await self._check_unique_indexes(collection, unique_constraints)
                if missing_indexes:
                    warnings.extend(missing_indexes)
                    logging.warning(f"Missing unique indexes for {collection}: {missing_indexes}")
            
            await es.index(index=collection, id=doc_id, document=data)
            # Get the saved document (this returns tuple, so unpack)
            saved_doc, get_warnings = await self.get_by_id(collection, doc_id)
            warnings.extend(get_warnings)
            return saved_doc, warnings
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="save_document"
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
            return [{**hit["_source"], self.id_field: hit[self.id_field]} for hit in hits]
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
                missing_constraints.append(f"Elasticsearch does not support unique constraints on {constraint_desc}")
            
            return missing_constraints
            
        except Exception as e:
            logging.warning(f"Failed to check unique constraints for {collection}: {str(e)}")
            return []