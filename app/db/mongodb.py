import logging
from typing import Any, Dict, List, Optional, Type, Union, cast, Tuple
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from pydantic import ValidationError as PydanticValidationError
from pymongo.errors import DuplicateKeyError

from .base import DatabaseInterface, T, SyntheticDuplicateError
from ..errors import DatabaseError, ValidationError, ValidationFailure, DuplicateError, NotFoundError

class MongoDatabase(DatabaseInterface):
    def __init__(self):
        super().__init__()
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    @property
    def id_field(self) -> str:
        return "_id"

    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize the ID from a MongoDB document"""
        if not document:
            return None
        
        # MongoDB uses _id field
        id_value = document.get(self.id_field)
        if id_value is None:
            return None
            
        # Convert ObjectId to string if needed
        if isinstance(id_value, ObjectId):
            return str(id_value)
        
        return str(id_value) if id_value else None

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
                # Convert ObjectId to string and normalize to 'id' field
                if self.id_field in doc:
                    doc['id'] = str(doc[self.id_field])
                    del doc[self.id_field]  # Remove _id, replace with id
                results.append(cast(Dict[str, Any], doc))
            
            return results, warnings, total_count
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_all"
            )

    async def get_list(self, collection: str, unique_constraints: Optional[List[List[str]]] = None, list_params=None, entity_metadata: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[str], int]:
        """Get paginated/filtered list of documents from a collection with count."""
        self._ensure_initialized()
        
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
            
            # Build MongoDB aggregation pipeline
            pipeline = []
            
            # Build match stage for filtering
            match_query = self._build_query_filter(list_params, entity_metadata)
            if match_query:
                pipeline.append({"$match": match_query})
            
            # Use facet to get both data and count in one query
            facet_pipeline = {
                "data": [],
                "count": [{"$count": "total"}]
            }
            
            # Add sorting to data pipeline
            sort_spec = self._build_sort_spec(list_params)
            if sort_spec:
                facet_pipeline["data"].append({"$sort": sort_spec})
            
            # Add pagination to data pipeline
            facet_pipeline["data"].extend([
                {"$skip": list_params.skip},
                {"$limit": list_params.page_size}
            ])
            
            pipeline.append({"$facet": facet_pipeline})
            
            # Execute aggregation
            cursor = self._get_db()[collection].aggregate(pipeline)
            result = await cursor.to_list(1)
            
            if not result:
                return [], warnings, 0
            
            facet_result = result[0]
            raw_data = facet_result.get("data", [])
            count_result = facet_result.get("count", [])
            total_count = count_result[0]["total"] if count_result else 0
            
            # Process results (normalize IDs)
            results = []
            for doc in raw_data:
                if self.id_field in doc:
                    doc['id'] = str(doc[self.id_field])
                    del doc[self.id_field]  # Remove _id, replace with id
                results.append(cast(Dict[str, Any], doc))
            
            return results, warnings, total_count
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=collection,
                operation="get_list"
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
                raise NotFoundError(collection, doc_id)
                
            # Convert ObjectId to string and normalize to 'id' field
            if self.id_field in doc:
                doc['id'] = str(doc[self.id_field])
                del doc[self.id_field]  # Remove _id, replace with id
                
            return cast(Dict[str, Any], doc), warnings
                
        except NotFoundError:
            # Re-raise NotFoundError so it can be handled by FastAPI
            raise
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
            
            # Prepare document with synthetic hash fields if needed (no-op for MongoDB)
            prepared_data = await self.prepare_document_for_save(collection, data, unique_constraints)
            
            # Validate unique constraints before save (no-op for MongoDB)
            await self.validate_unique_constraints_before_save(collection, prepared_data, unique_constraints)
            
            # Extract ID from data 
            doc_id = prepared_data.get('id')
            
            # Create a copy of data for the actual save operation
            save_data = prepared_data.copy()
            
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
            
        except DuplicateKeyError as e:
            # Parse MongoDB duplicate key error to get field and value
            field_name, field_value = self._parse_duplicate_key_error(e)
            raise DuplicateError(
                entity=collection,
                field=field_name,
                value=field_value
            )
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

    def _parse_duplicate_key_error(self, error: DuplicateKeyError) -> Tuple[str, str]:
        """
        Parse MongoDB duplicate key error to extract field name and value.
        
        Args:
            error: The DuplicateKeyError from MongoDB
            
        Returns:
            Tuple of (field_name, field_value)
        """
        try:
            # Get the details from the error
            if hasattr(error, 'details') and error.details:
                key_value = error.details.get('keyValue', {})
                if key_value:
                    # Get the first field name and value from the key
                    field_name = next(iter(key_value.keys()))
                    field_value = str(key_value[field_name])
                    return field_name, field_value
            
            # Fallback: parse from error message
            error_str = str(error)
            if 'dup key:' in error_str:
                # Extract field name from index name (e.g. "username_1" -> "username")
                if 'index:' in error_str:
                    index_part = error_str.split('index:')[1].split('dup key:')[0].strip()
                    field_name = index_part.split('_')[0]  # Remove _1 suffix
                else:
                    field_name = 'unknown'
                
                # Extract value from dup key part
                if '{ ' in error_str and ' }' in error_str:
                    dup_key_part = error_str.split('dup key:')[1].split('}')[0] + '}'
                    # Simple parsing to get the value
                    if '"' in dup_key_part:
                        field_value = dup_key_part.split('"')[1]
                    else:
                        field_value = 'unknown'
                else:
                    field_value = 'unknown'
                
                return field_name, field_value
            
            return 'unknown', 'unknown'
            
        except Exception:
            # If parsing fails, return generic info
            return 'unknown', 'unknown'

    async def supports_native_indexes(self) -> bool:
        """MongoDB supports native unique indexes"""
        return True
    
    async def document_exists_with_field_value(self, collection: str, field: str, value: Any, exclude_id: Optional[str] = None) -> bool:
        """Check if document exists with field value (not needed for MongoDB - native indexes handle this)"""
        return False

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
    
    def _build_query_filter(self, list_params, entity_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build MongoDB query from ListParams with field-type awareness."""
        if not list_params or not list_params.filters:
            return {}
        
        query = {}
        for field, value in list_params.filters.items():
            if isinstance(value, dict) and ('$gte' in value or '$lte' in value):
                # Range filter - use as-is
                query[field] = value
            else:
                # Determine matching strategy based on field type
                field_type = self._get_field_type(field, entity_metadata)
                if field_type == 'String':
                    # Text fields: partial match with regex
                    query[field] = {"$regex": f".*{self._escape_regex(str(value))}.*", "$options": "i"}
                else:
                    # Non-text fields (enums, numbers, dates, etc.): exact match
                    query[field] = value
        
        return query

    def _build_sort_spec(self, list_params) -> Dict[str, int]:
        """Build MongoDB sort specification from ListParams."""
        if not list_params or not list_params.sort_field:
            return {}
        return {list_params.sort_field: 1 if list_params.sort_order == "asc" else -1}

    def _get_field_type(self, field_name: str, entity_metadata: Optional[Dict[str, Any]]) -> str:
        """Get field type from entity metadata or default to String."""
        if not entity_metadata or 'fields' not in entity_metadata:
            return 'String'  # Default to string for partial matching
        
        field_info = entity_metadata.get('fields', {}).get(field_name, {})
        field_type = field_info.get('type', 'String')
        
        # Check if field has enum values - treat as exact match even if type is String
        if 'enum' in field_info:
            return 'Enum'  # Use exact matching for enum fields
        
        return field_type

    def _escape_regex(self, text: str) -> str:
        """Escape special regex characters in search text."""
        import re
        return re.escape(text)

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
                    missing_constraints.append(f"Missing unique index for {constraint_desc} - run with --initdb to create indexes")
            
            return missing_constraints
            
        except Exception as e:
            # Return empty list on error - Factory layer will handle notification
            return [] 