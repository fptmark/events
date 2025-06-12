import logging
from typing import Any, Dict, List, Optional, Type, Union
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
from pydantic import BaseModel, ValidationError as PydanticValidationError
from bson.objectid import ObjectId

from .base import DatabaseInterface, T  # assuming T is your generic Pydantic model type
from ..errors import DatabaseError, ValidationError, ValidationFailure

class MongoDatabase(DatabaseInterface):
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    @property
    def id_field(self) -> str:
        return "_id"

    async def init(self, connection_str: str, database_name: str) -> None:
        if self._client:
            logging.info("MongoDatabase: Already initialized")
            return
        self._client = AsyncIOMotorClient(connection_str)
        self._db = self._client[database_name]

        # Test connection
        try:
            await self._client.admin.command('ping')
            logging.info(f"MongoDatabase: Connected to {database_name}")
        except Exception as e:
            raise DatabaseError(
                message=f"MongoDB connection failed: {str(e)}",
                entity="connection",
                operation="init"
            )

    async def find_all(self, collection: str, model_cls: Type[T]) -> tuple[List[T], List[ValidationError]]:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        cursor = self._db[collection].find()
        results = []
        validation_errors = []
        async for doc in cursor:
            try:
                # Convert ObjectId to string
                if '_id' in doc and not isinstance(doc['_id'], str):
                    doc['_id'] = str(doc['_id'])
                results.append(self.validate_document(doc, model_cls))
            except ValidationError as ve:
                # Log the error and collect it
                logging.warning(
                    f"Validation failed for document {doc.get('_id')}: {ve.message}"
                )
                validation_errors.append(ve)
                continue
        return results, validation_errors

    async def get_by_id(self, collection: str, doc_id: Any, model_cls: Type[T]) -> Optional[T]:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
            
        # Convert string ID to ObjectId if it's a valid ObjectId string
        query_id = doc_id
        if isinstance(doc_id, str) and ObjectId.is_valid(doc_id):
            query_id = ObjectId(doc_id)
            
        doc = await self._db[collection].find_one({self.id_field: query_id})
        if not doc:
            return None
        try:
            # Convert ObjectId to string
            if '_id' in doc and not isinstance(doc['_id'], str):
                doc['_id'] = str(doc['_id'])
            return self.validate_document(doc, model_cls)
        except ValidationError as ve:
            # Log the error but raise it to be handled by our error handler
            logging.warning(
                f"Validation failed for document {doc_id}: {ve.message}"
            )
            raise ValidationError(
                message=f"Validation failed for document {doc_id}",
                entity=model_cls.__name__,
                invalid_fields=ve.invalid_fields
            )

    async def save_document(self, collection: str, doc_id: Optional[Any], data: Dict[str, Any], 
                          unique_constraints: Optional[List[List[str]]] = None) -> Union[UpdateResult, InsertOneResult]:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        
        try:
            # Check unique constraints if provided
            if unique_constraints:
                conflicting_fields = await self.check_unique_constraints(
                    collection, unique_constraints, data, doc_id
                )
                if conflicting_fields:
                    from ..errors import ValidationError, ValidationFailure
                    raise ValidationError(
                        message=f"Unique constraint violation for fields: {conflicting_fields}",
                        entity=collection,
                        invalid_fields=[
                            ValidationFailure(
                                field=field,
                                message="Value already exists",
                                value=data.get(field)
                            ) for field in conflicting_fields
                        ]
                    )
            
            if doc_id is not None:
                return await self._db[collection].replace_one({self.id_field: doc_id}, data, upsert=True)
            else:
                return await self._db[collection].insert_one(data)
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="save"
            )

    def validate_document(self, doc_data: Dict[str, Any], model_cls: Type[T]) -> T:
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

    async def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logging.info("MongoDatabase: Connection closed")

    async def collection_exists(self, collection: str) -> bool:
        """Check if a collection exists in MongoDB"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            collections = await self._db.list_collection_names()
            return collection in collections
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to check if collection '{collection}' exists: {str(e)}",
                entity=collection,
                operation="collection_exists"
            )

    async def _create_required_indexes(self, collection: str, required_indexes: List[Dict[str, Any]]) -> None:
        """Create required indexes for a collection based on metadata"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            # Create unique indexes
            for index in required_indexes:
                fields = index.get('fields', [])
                unique = index.get('unique', False)
                await self.create_index(collection, fields, unique)
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create indexes for collection '{collection}': {str(e)}",
                entity=collection,
                operation="create_indexes"
            )

    async def _ensure_collection_exists(self, collection: str) -> None:
        """Ensure a collection exists, create it if it doesn't"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            if not await self.collection_exists(collection):
                await self.create_collection(collection)
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to ensure collection '{collection}' exists: {str(e)}",
                entity=collection,
                operation="ensure_collection"
            )

    async def check_unique_constraints(self, collection: str, constraints: List[List[str]], 
                                     data: Dict[str, Any], exclude_id: Optional[str] = None) -> List[str]:
        """Check if any unique constraints would be violated"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            conflicting_fields = []
            for fields in constraints:
                query = {field: data.get(field) for field in fields if field in data}
                if not query:
                    continue
                
                if exclude_id:
                    query[self.id_field] = {"$ne": exclude_id}
                
                if await self._db[collection].find_one(query):
                    conflicting_fields.extend(fields)
            return conflicting_fields
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to check unique constraints: {str(e)}",
                entity=collection,
                operation="check_unique_constraints"
            )

    async def create_collection(self, collection: str, **kwargs) -> bool:
        """Create a new collection"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            await self._db.create_collection(collection)
            return True
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create collection '{collection}': {str(e)}",
                entity=collection,
                operation="create_collection"
            )

    async def create_index(self, collection: str, fields: List[str], unique: bool = False, **kwargs) -> bool:
        """Create an index on a collection"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            index_spec = [(field, 1) for field in fields]
            await self._db[collection].create_index(index_spec, unique=unique)
            return True
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create index on {collection}: {str(e)}",
                entity=collection,
                operation="create_index"
            )

    async def delete_collection(self, collection: str) -> bool:
        """Delete a collection"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            await self._db.drop_collection(collection)
            return True
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete collection '{collection}': {str(e)}",
                entity=collection,
                operation="delete_collection"
            )

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document by ID"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            result = await self._db[collection].delete_one({self.id_field: doc_id})
            return result.deleted_count > 0
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete document: {str(e)}",
                entity=collection,
                operation="delete_document"
            )

    async def delete_index(self, collection: str, index_name: str) -> bool:
        """Delete an index from a collection"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            await self._db[collection].drop_index(index_name)
            return True
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete index from {collection}: {str(e)}",
                entity=collection,
                operation="delete_index"
            )

    async def exists(self, collection: str, doc_id: str) -> bool:
        """Check if a document exists"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            return await self._db[collection].count_documents({self.id_field: doc_id}) > 0
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to check document existence: {str(e)}",
                entity=collection,
                operation="exists"
            )

    async def list_collections(self) -> List[str]:
        """List all collections in the database"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            return await self._db.list_collection_names()
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to list collections: {str(e)}",
                entity="database",
                operation="list_collections"
            )

    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes on a collection"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            indexes = []
            async for index in self._db[collection].list_indexes():
                indexes.append(index)
            return indexes
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to list indexes: {str(e)}",
                entity=collection,
                operation="list_indexes"
            ) 