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
        try:
            res = await es.get(index=collection, id=doc_id)
            doc_data = {**res["_source"], self.id_field: res[self.id_field]}
            return self.validate_document(doc_data, model_cls)
        except NotFoundError:
            return None
        except ValidationError:
            # Re-raise validation errors as is
            raise
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_by_id"
            )

    async def save_document(self, collection: str, doc_id: Optional[str],
                          data: Dict[str, Any]) -> ObjectApiResponse[Any]:
        """Save a document to Elasticsearch"""
        es = self._get_client()

        try:
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
            return await es.exists(index=collection, id=doc_id)
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
                    if "index_not_found_exception" in str(search_error):
                        # Index doesn't exist, collect missing constraint info
                        if len(unique_fields) == 1:
                            missing_constraints.append(f"unique constraint on {unique_fields[0]}")
                        else:
                            missing_constraints.append(f"composite unique constraint on ({', '.join(unique_fields)})")
                    else:
                        logging.error(f"Error checking uniqueness for {unique_fields}: {search_error}")
                        # For other errors, continue checking remaining constraints
                        continue
            
            # After checking all constraints, raise error if any are missing
            if missing_constraints:
                from ..errors import ValidationError, ValidationFailure
                constraint_list = "; ".join(missing_constraints)
                raise ValidationError(
                    message=f"{collection.title()} operation failed: Required constraints missing: {constraint_list}",
                    entity=collection,
                    invalid_fields=[
                        ValidationFailure(
                            field="constraints",
                            message="Missing required indexes",
                            value=constraint_list
                        )
                    ]
                )
                    
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