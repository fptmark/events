import logging
from typing import Any, Dict, List, Optional, Type, Union
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.results import InsertOneResult, UpdateResult
from pydantic import BaseModel, ValidationError as PydanticValidationError

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

    async def find_all(self, collection: str, model_cls: Type[T]) -> List[T]:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        cursor = self._db[collection].find()
        results = []
        async for doc in cursor:
            try:
                results.append(self.validate_document(doc, model_cls))
            except ValidationError as ve:
                logging.warning(f"Validation failed for document {doc.get('_id')}: {ve}")
                continue
        return results

    async def get_by_id(self, collection: str, doc_id: Any, model_cls: Type[T]) -> Optional[T]:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        doc = await self._db[collection].find_one({self.id_field: doc_id})
        if not doc:
            return None
        return self.validate_document(doc, model_cls)

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

    async def delete_document(self, collection: str, doc_id: Any) -> bool:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        result = await self._db[collection].delete_one({self.id_field: doc_id})
        return result.deleted_count > 0

    async def check_unique_constraints(
        self,
        collection: str,
        constraints: List[List[str]],
        data: Dict[str, Any],
        exclude_id: Optional[Any] = None,
    ) -> List[str]:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        conflicting_fields = []
        for constraint in constraints:
            query = {field: data.get(field) for field in constraint}
            if exclude_id is not None:
                query[self.id_field] = {"$ne": exclude_id}
            exists = await self._db[collection].find_one(query)
            if exists:
                conflicting_fields.extend(constraint)
        return conflicting_fields

    async def exists(self, collection: str, doc_id: Any) -> bool:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        doc = await self._db[collection].find_one({self.id_field: doc_id})
        return doc is not None

    async def list_collections(self) -> List[str]:
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        return await self._db.list_collection_names()

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

    async def create_collection(self, collection: str, **kwargs) -> bool:
        """Create a collection in MongoDB"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            if await self.collection_exists(collection):
                return False  # Already exists
            
            # Create collection with optional settings
            await self._db.create_collection(collection, **kwargs)
            logging.info(f"Created collection: {collection}")
            return True
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create collection '{collection}': {str(e)}",
                entity=collection,
                operation="create_collection"
            )

    async def delete_collection(self, collection: str) -> bool:
        """Delete a collection from MongoDB"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            if not await self.collection_exists(collection):
                return False  # Doesn't exist
            
            await self._db.drop_collection(collection)
            logging.info(f"Deleted collection: {collection}")
            return True
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete collection '{collection}': {str(e)}",
                entity=collection,
                operation="delete_collection"
            )

    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes for a specific MongoDB collection"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            indexes = []
            async for index_info in self._db[collection].list_indexes():
                # Extract index information
                index_name = index_info.get('name', '')
                key_spec = index_info.get('key', {})
                
                # Convert MongoDB key spec to field list
                fields = list(key_spec.keys())
                
                # Check if it's unique
                unique = index_info.get('unique', False)
                
                # Check if it's a system index (like _id_)
                system = index_name == '_id_'
                
                indexes.append({
                    'name': index_name,
                    'fields': fields,
                    'unique': unique,
                    'system': system
                })
            
            return indexes
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to list indexes for collection '{collection}': {str(e)}",
                entity=collection,
                operation="list_indexes"
            )

    async def create_index(self, collection: str, fields: List[str], unique: bool = False, **kwargs) -> bool:
        """Create an index on specific fields in MongoDB"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            # Check if collection exists
            if not await self.collection_exists(collection):
                return False  # Collection doesn't exist
            
            # Build index specification
            index_spec = [(field, 1) for field in fields]  # 1 for ascending
            
            # Create index with optional uniqueness
            index_name = f"{'unique_' if unique else ''}{'_'.join(fields)}"
            await self._db[collection].create_index(
                index_spec, 
                unique=unique, 
                name=index_name,
                **kwargs
            )
            
            logging.info(f"Created index '{index_name}' on {fields} in collection {collection}")
            return True
            
        except Exception as e:
            # Check if it's a duplicate key error (index already exists)
            if "already exists" in str(e).lower():
                return False  # Index already exists
            raise DatabaseError(
                message=f"Failed to create index on {fields} for collection '{collection}': {str(e)}",
                entity=collection,
                operation="create_index"
            )

    async def delete_index(self, collection: str, index_name: str) -> bool:
        """Delete a specific index from MongoDB collection"""
        if self._db is None:
            raise RuntimeError("MongoDatabase not initialized")
        try:
            # Check if collection exists
            if not await self.collection_exists(collection):
                return False  # Collection doesn't exist
            
            # Cannot delete the _id_ index
            if index_name == '_id_':
                logging.warning(f"Cannot delete system index '_id_' in collection '{collection}'")
                return False
            
            await self._db[collection].drop_index(index_name)
            logging.info(f"Deleted index '{index_name}' from collection {collection}")
            return True
            
        except Exception as e:
            # Check if it's a "index not found" error
            if "index not found" in str(e).lower():
                return False  # Index doesn't exist
            raise DatabaseError(
                message=f"Failed to delete index '{index_name}' from collection '{collection}': {str(e)}",
                entity=collection,
                operation="delete_index"
            )

    async def _ensure_collection_exists(self, collection: str) -> None:
        """Ensure a MongoDB collection exists, creating it if necessary"""
        if not await self.collection_exists(collection):
            logging.info(f"Creating collection '{collection}'")
            await self.create_collection(collection)

    async def _create_required_indexes(self, collection: str, required_indexes: List[Dict[str, Any]]) -> None:
        """Create required indexes for a MongoDB collection"""
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
