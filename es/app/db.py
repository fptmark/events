from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar

from elastic_transport import ObjectApiResponse
from elasticsearch import AsyncElasticsearch, NotFoundError
from pydantic import BaseModel

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
        hasn’t been awaited in this process.
        """
        if cls._client is None:  # mypy now knows this can’t be None later
            raise RuntimeError("Database.init() has not been awaited")
        return cls._client

    # --------------------------------------------------------- convenience
    @classmethod
    async def find_all(cls, index: str, model_cls: Type[T]) -> List[T]:
        es = cls.client()

        if not await es.indices.exists(index=index):
            return []

        try:
            res = await es.search(index=index, query={"match_all": {}})
        except Exception:
            res = await es.search(index=index, body={"query": {"match_all": {}}})

        hits = res.get("hits", {}).get("hits", [])
        return [model_cls.model_validate({**h["_source"], "_id": h["_id"]})
                for h in hits]

    @classmethod
    async def get_by_id(cls, index: str, doc_id: str,
                        model_cls: Type[T]) -> Optional[T]:
        es = cls.client()
        try:
            res = await es.get(index=index, id=doc_id)
        except NotFoundError:
            return None
        return model_cls.model_validate({**res["_source"], "_id": res["_id"]})

    @classmethod
    async def save_document(cls, index: str, doc_id: Optional[str],
                            data: Dict[str, Any]) -> ObjectApiResponse[Any]:
        es = cls.client()

        if not await es.indices.exists(index=index):
            await es.indices.create(index=index)

        return (await es.index(index=index, id=doc_id, document=data)
                if doc_id else
                await es.index(index=index, document=data))

    @classmethod
    async def delete_document(cls, index: str, doc_id: str) -> bool:
        es = cls.client()
        if not await es.exists(index=index, id=doc_id):
            return False
        await es.delete(index=index, id=doc_id)
        return True

    # ------------------------------------------------------------ cleanup
    @classmethod
    async def close(cls) -> None:
        """Close the ES connection when your process shuts down."""
        if cls._client is not None:
            await cls._client.close()
            cls._client = None
