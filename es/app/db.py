import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, cast, ClassVar

from elastic_transport import ObjectApiResponse
from elasticsearch import AsyncElasticsearch, NotFoundError
from pydantic import BaseModel, ValidationError as PydanticValidationError

from .errors import DatabaseError, ValidationError, ValidationFailure

T = TypeVar("T", bound=BaseModel)


class Database:
    """
    Process‑wide singleton wrapper around AsyncElasticsearch.

    Call `await Database.init(url, db)` **once per interpreter** (e.g. in a
    FastAPI `@app.on_event("startup")`).  Afterwards use `Database.client()`
    or the convenience helpers.
    """

    _client: Optional[AsyncElasticsearch] = None
    _url: str = ""
    _dbname: str = ""

    # Database-specific ID field name
    ID_FIELD: ClassVar[str] = "_id"

    @classmethod
    def get_id_field(cls) -> str:
        """Get the database-specific ID field name"""
        return cls.ID_FIELD

    # ------------------------------------------------------------------ init
    @classmethod
    async def init(cls, url: str, dbname: str) -> None:
        """
        Initialise the singleton.  Safe to call multiple times; subsequent
        calls are ignored.
        """
        if cls._client is not None:
            logging.info("Elasticsearch already initialised – re‑using client")
            return

        cls._url, cls._dbname = url, dbname
        client = AsyncElasticsearch(hosts=[url])

        # fail fast if ES is down
        info = await client.info()
        logging.info("Connected to Elasticsearch %s", info["version"]["number"])

        cls._client = client

    # ------------------------------------------------------------- accessor
    @classmethod
    def client(cls) -> AsyncElasticsearch:
        """
        Return the shared AsyncElasticsearch instance, or raise if `init`
        hasn't been awaited in this process.
        """
        if cls._client is None:  # mypy now knows this can't be None later
            raise RuntimeError("Database.init() has not been awaited")
        return cls._client

    @classmethod
    def _validate_document(cls, doc_data: Dict[str, Any], model_cls: Type[T]) -> T:
        """Validate document data against model and return instance"""
        try:
            return model_cls.model_validate(doc_data)
        except PydanticValidationError as e:
            # Convert Pydantic validation error to our standard format
            errors = e.errors()
            if errors:
                failures = [
                    ValidationFailure(
                        field=str(err["loc"][-1]),
                        message=err["msg"],
                        value=err.get("input")
                    )
                    for err in errors
                ]
                raise ValidationError(
                    message="Validation failed",
                    entity=model_cls.__name__,
                    invalid_fields=failures
                )
            raise ValidationError(
                message="Validation failed",
                entity=model_cls.__name__,
                invalid_fields=[]
            )

    # --------------------------------------------------------- convenience
    @classmethod
    async def find_all(cls, index: str, model_cls: Type[T]) -> List[T]:
        es = cls.client()

        if not await es.indices.exists(index=index):
            return []

        try:
            res = await es.search(index=index, query={"match_all": {}})
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=index,
                operation="find_all"
            )

        hits = res.get("hits", {}).get("hits", [])
        validated_docs = []
        
        for hit in hits:
            try:
                doc_data = {**hit["_source"], cls.ID_FIELD: hit[cls.ID_FIELD]}
                validated_docs.append(cls._validate_document(doc_data, model_cls))
            except ValidationError as e:
                logging.error(f"Validation failed for document {hit[cls.ID_FIELD]}: {e.message}")
                # Skip invalid documents but continue processing
                continue
                
        return validated_docs

    @classmethod
    async def get_by_id(cls, index: str, doc_id: str, model_cls: Type[T]) -> Optional[T]:
        es = cls.client()
        try:
            res = await es.get(index=index, id=doc_id)
            doc_data = {**res["_source"], cls.ID_FIELD: res[cls.ID_FIELD]}
            return cls._validate_document(doc_data, model_cls)
        except NotFoundError:
            return None
        except ValidationError:
            # Re-raise validation errors as is
            raise
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=index,
                operation="get_by_id"
            )

    @classmethod
    async def save_document(cls, index: str, doc_id: Optional[str],
                          data: Dict[str, Any]) -> ObjectApiResponse[Any]:
        es = cls.client()

        try:
            if not await es.indices.exists(index=index):
                await es.indices.create(index=index)

            return (await es.index(index=index, id=doc_id, document=data)
                    if doc_id else
                    await es.index(index=index, document=data))
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=index,
                operation="save"
            )

    @classmethod
    async def delete_document(cls, index: str, doc_id: str) -> bool:
        es = cls.client()
        try:
            if not await es.exists(index=index, id=doc_id):
                return False
            await es.delete(index=index, id=doc_id)
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=index,
                operation="delete"
            )

    # ------------------------------------------------------------ cleanup
    @classmethod
    async def close(cls) -> None:
        """Close the ES connection when your process shuts down."""
        if cls._client is not None:
            await cls._client.close()
            cls._client = None