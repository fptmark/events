import logging
from typing import Any, Dict, List, Optional, Type, Union, cast, Tuple
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import ValidationError as PydanticValidationError

from .base import DatabaseInterface, T
from ..errors import DatabaseError, ValidationError, ValidationFailure

class MongoDatabase(DatabaseInterface):
    def __init__(self):
        super().__init__()
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    @property
    def id_field(self) -> str:
        return "_id"

    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize MongoDB connection."""
        if self._client is not None:
            logging.info("MongoDatabase: Already initialized")
            return

        try:
            self._client = AsyncIOMotorClient(connection_str)
            self._db = self._client[database_name]
            
            # Test connection
            await self._client.admin.command('ping')
            self._initialized = True
            logging.info(f"MongoDatabase: Connected to {database_name}")
        except Exception as e:
            # Cleanup on failure
            if self._client:
                self._client.close()
                self._client = None
                self._db = None
            self._handle_connection_error(e, database_name)

    def _get_db(self) -> AsyncIOMotorDatabase:
        """Get the database instance with proper type checking."""
        self._ensure_initialized()
        if self._db is None:
            raise DatabaseError(
                message="Database not initialized",
                entity="database",
                operation="get_db"
            )
        return self._db

    async def get_all(self, collection: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Get all documents from a collection with count."""
        self._ensure_initialized()
            
        try:
            warnings = []
            # Check unique constraints if provided
            if unique_constraints:
                missing_indexes = await self._check_unique_indexes(collection, unique_constraints)
                if missing_indexes:
                    warnings.extend(missing_indexes)
            
            # Get total count
            total_count = await self._get_db()[collection].count_documents({})
            
            cursor = self._get_db()[collection].find()
            results = []
            async for doc in cursor:
                # Convert ObjectId to string for consistency
                if self.id_field in doc and isinstance(doc[self.id_field], ObjectId):
                    doc[self.id_field] = str(doc[self.id_field])
                results.append(cast(Dict[str, Any], doc))
            
            return results, warnings, total_count
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_all"
            )

    async def get_by_id(self, collection: str, doc_id: str, unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Get a document by ID."""
        self._ensure_initialized()
            
        try:
            warnings = []
            # Check unique constraints if provided
            if unique_constraints:
                missing_indexes = await self._check_unique_indexes(collection, unique_constraints)
                if missing_indexes:
                    warnings.extend(missing_indexes)
            
            # Convert string ID to ObjectId if it's a valid ObjectId string
            query_id: Union[str, ObjectId] = doc_id
            if isinstance(doc_id, str) and ObjectId.is_valid(doc_id):
                query_id = ObjectId(doc_id)
                
            # Get document
            doc = await self._get_db()[collection].find_one({self.id_field: query_id})
            if doc is None:
                raise DatabaseError(
                    message=f"Document not found: {doc_id}",
                    entity=collection,
                    operation="get_by_id"
                )
                
            # Convert ObjectId to string for consistency
            if self.id_field in doc and isinstance(doc[self.id_field], ObjectId):
                doc[self.id_field] = str(doc[self.id_field])
                
            return cast(Dict[str, Any], doc), warnings
                
        except DatabaseError:
            # Re-raise database errors
            raise
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_by_id"
            )

    async def save_document(self, collection: str, data: Dict[str, Any], unique_constraints: Optional[List[List[str]]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """Save a document to the database."""
        self._ensure_initialized()
            
        try:
            warnings = []
            # Check unique constraints if provided
            if unique_constraints:
                missing_indexes = await self._check_unique_indexes(collection, unique_constraints)
                if missing_indexes:
                    warnings.extend(missing_indexes)
            
            # Extract ID from data 
            doc_id = data.get('id')
            
            # Create a copy of data for the actual save operation
            save_data = data.copy()
            
            # Handle new documents (no ID) vs updates (existing ID)
            if not doc_id or (isinstance(doc_id, str) and doc_id.strip() == ""):
                # New document: let MongoDB auto-generate _id
                # Remove any empty ID fields from save data
                save_data.pop('id', None)
                result = await self._get_db()[collection].insert_one(save_data)
                doc_id_str = str(result.inserted_id)
            else:
                # Existing document: update with specific ID
                query_id: Union[str, ObjectId] = doc_id
                if isinstance(doc_id, str) and ObjectId.is_valid(doc_id):
                    query_id = ObjectId(doc_id)
                
                # Remove ID from save data since it's used in query
                save_data.pop('id', None) 
                    
                # Update existing document
                result = await self._get_db()[collection].replace_one({self.id_field: query_id}, save_data, upsert=True)
                doc_id_str = str(query_id) if isinstance(query_id, ObjectId) else query_id
                
            # Get the saved document (this will return tuple, so unpack)
            saved_doc, get_warnings = await self.get_by_id(collection, doc_id_str)
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
            self._client.close()
            self._client = None
            self._db = None
            logging.info("MongoDatabase: Connection closed")

    async def collection_exists(self, collection: str) -> bool:
        """Check if a collection exists."""
        self._ensure_initialized()
            
        try:
            collections = await self._get_db().list_collection_names()
            return collection in collections
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="collection_exists"
            )

    async def create_collection(self, collection: str, indexes: List[Dict[str, Any]]) -> bool:
        """Create a collection with indexes."""
        self._ensure_initialized()
            
        try:
            # Create collection
            await self._get_db().create_collection(collection)
            
            # Create indexes
            await self._create_required_indexes(collection, indexes)
                
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="create_collection"
            )

    async def _create_required_indexes(self, collection: str, indexes: List[Dict[str, Any]]) -> None:
        """Create required indexes for a collection."""
        self._ensure_initialized()
            
        for index in indexes:
            try:
                await self._get_db()[collection].create_index(
                    index['fields'],
                    unique=index.get('unique', False),
                    name=index.get('name')
                )
            except Exception as e:
                raise DatabaseError(
                    message=str(e),
                    entity=collection,
                    operation="create_index"
                )

    async def delete_collection(self, collection: str) -> bool:
        """Delete a collection."""
        self._ensure_initialized()
            
        try:
            await self._get_db().drop_collection(collection)
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="delete_collection"
            )

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document."""
        self._ensure_initialized()
            
        try:
            # Convert string ID to ObjectId if it's a valid ObjectId string
            query_id: Union[str, ObjectId] = doc_id
            if isinstance(doc_id, str) and ObjectId.is_valid(doc_id):
                query_id = ObjectId(doc_id)
                
            result = await self._get_db()[collection].delete_one({self.id_field: query_id})
            return result.deleted_count > 0
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="delete_document"
            )

    async def list_collections(self) -> List[str]:
        """List all collections."""
        self._ensure_initialized()
            
        try:
            return await self._get_db().list_collection_names()
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity="collections",
                operation="list_collections"
            )

    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes for a collection."""
        self._ensure_initialized()
            
        try:
            raw_indexes = await self._get_db()[collection].list_indexes().to_list(None)
            standardized_indexes = []
            
            for raw_idx in raw_indexes:
                # Extract field names from MongoDB key structure
                fields = []
                if 'key' in raw_idx:
                    fields = list(raw_idx['key'].keys())
                
                # Determine if it's a system index
                name = raw_idx.get('name', '')
                is_system = name == '_id_' or name.startswith('_')
                
                # Determine if it's unique
                is_unique = raw_idx.get('unique', False)
                
                standardized_indexes.append({
                    'name': name,
                    'fields': fields,
                    'unique': is_unique,
                    'system': is_system
                })
            
            return standardized_indexes
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="list_indexes"
            )

    async def find_all(self, collection: str, model_cls: Type[T]) -> List[T]:
        """Get all documents from a collection and validate them against a model class."""
        self._ensure_initialized()
            
        try:
            cursor = self._get_db()[collection].find()
            results = []
            async for doc in cursor:
                try:
                    # Convert ObjectId to string for consistency
                    if self.id_field in doc and isinstance(doc[self.id_field], ObjectId):
                        doc[self.id_field] = str(doc[self.id_field])
                    results.append(model_cls.model_validate(doc))
                except PydanticValidationError as e:
                    # Convert Pydantic validation error to our standard format
                    failures = [
                        ValidationFailure(
                            field=str(err["loc"][-1]),
                            message=err["msg"],
                            value=err.get("input")
                        ) for err in e.errors()
                    ]
                    raise ValidationError(
                        message=f"Validation failed for document {doc.get('_id')}",
                        entity=model_cls.__name__,
                        invalid_fields=failures
                    )
            return results
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="find_all"
            )

    def validate_document(self, doc_data: Dict[str, Any], model_cls: Type[T]) -> T:
        """Validate a document against a model class."""
        try:
            # Convert ObjectId to string for consistency
            if self.id_field in doc_data and isinstance(doc_data[self.id_field], ObjectId):
                doc_data[self.id_field] = str(doc_data[self.id_field])
            return model_cls.model_validate(doc_data)
        except PydanticValidationError as e:
            # Convert Pydantic validation error to our standard format
            failures = [
                ValidationFailure(
                    field=str(err["loc"][-1]),
                    message=err["msg"],
                    value=err.get("input")
                ) for err in e.errors()
            ]
            raise ValidationError(
                message="Validation failed",
                entity=model_cls.__name__,
                invalid_fields=failures
            )

    async def _ensure_collection_exists(self, collection: str, indexes: List[Dict[str, Any]]) -> None:
        """Ensure a collection exists with required indexes."""
        if not await self.collection_exists(collection):
            await self.create_collection(collection, indexes)

    async def check_unique_constraints(self, collection: str, constraints: List[List[str]], 
                                     data: Dict[str, Any], exclude_id: Optional[str] = None) -> List[str]:
        """Check unique constraints on a document."""
        self._ensure_initialized()
            
        try:
            violations = []
            for fields in constraints:
                # Build query for unique constraint
                query = {field: data[field] for field in fields if field in data}
                if not query:
                    continue
                    
                # Exclude current document if updating
                if exclude_id:
                    query[self.id_field] = {"$ne": exclude_id}
                    
                # Check if any document matches
                if await self._get_db()[collection].find_one(query):
                    violations.append(f"Unique constraint violation on fields: {', '.join(fields)}")
                    
            return violations
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="check_unique_constraints"
            )

    async def create_index(self, collection: str, fields: List[str], unique: bool = False) -> None:
        """Create an index on a collection."""
        self._ensure_initialized()
            
        try:
            await self._get_db()[collection].create_index(
                [(field, 1) for field in fields],
                unique=unique
            )
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="create_index"
            )

    async def delete_index(self, collection: str, fields: List[str]) -> None:
        """Delete an index from a collection."""
        self._ensure_initialized()
            
        try:
            await self._get_db()[collection].drop_index([(field, 1) for field in fields])
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="delete_index"
            )

    async def exists(self, collection: str, doc_id: str) -> bool:
        """Check if a document exists."""
        self._ensure_initialized()
            
        try:
            # Convert string ID to ObjectId if it's a valid ObjectId string
            query_id: Union[str, ObjectId] = doc_id
            if isinstance(doc_id, str) and ObjectId.is_valid(doc_id):
                query_id = ObjectId(doc_id)
                
            result = await self._get_db()[collection].count_documents({self.id_field: query_id})
            return result > 0
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
            # Get existing indexes using our standardized format
            existing_indexes = await self.list_indexes(collection)
            existing_unique_indexes = [idx for idx in existing_indexes if idx.get('unique', False)]
            
            missing_constraints = []
            for constraint_fields in unique_constraints:
                # Check if this constraint has a corresponding unique index
                constraint_exists = False
                for idx in existing_unique_indexes:
                    idx_fields = idx.get('fields', [])
                    # Check if the index fields match the constraint fields (order doesn't matter)
                    if set(idx_fields) == set(constraint_fields):
                        constraint_exists = True
                        break
                
                if not constraint_exists:
                    constraint_desc = " + ".join(constraint_fields) if len(constraint_fields) > 1 else constraint_fields[0]
                    missing_constraints.append(f"unique constraint on {constraint_desc}")
            
            return missing_constraints
            
        except Exception as e:
            # Return empty list on error - Factory layer will handle notification
            return [] 