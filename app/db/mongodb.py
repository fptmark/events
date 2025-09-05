"""
MongoDB implementation of the database interface.
Each manager is implemented as a separate class for clean separation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from .base import DatabaseInterface
from .core_manager import CoreManager
from .document_manager import DocumentManager
from .entity_manager import EntityManager
from .index_manager import IndexManager
from ..errors import DatabaseError
from app.services.notification import duplicate_warning, validation_warning, not_found_warning
from app.services.metadata import MetadataService


class MongoCore(CoreManager):
    """MongoDB implementation of core operations"""
    
    def __init__(self, parent: 'MongoDatabase'):
        self.parent = parent
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
    
    @property
    def id_field(self) -> str:
        return "_id"
    
    async def init(self, connection_str: str, database_name: str) -> None:
        """Initialize MongoDB connection"""
        if self._client is not None:
            logging.info("MongoDatabase: Already initialized")
            return

        try:
            self._client = AsyncIOMotorClient(connection_str)
            self._db = self._client[database_name]
            
            # Test connection
            await self._client.admin.command('ping')
            self.parent._initialized = True
            logging.info(f"MongoDatabase: Connected to {database_name}")
            
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to connect to MongoDB: {str(e)}",
                entity="connection",
                operation="init"
            )
    
    async def close(self) -> None:
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self.parent._initialized = False
            logging.info("MongoDatabase: Connection closed")
    
    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize ID from MongoDB document"""
        if not document:
            return None
            
        id_value = document.get(self.id_field)
        if id_value is None:
            return None
            
        # Convert ObjectId to string
        if isinstance(id_value, ObjectId):
            return str(id_value)
        
        return str(id_value) if id_value else None
    
    def get_connection(self) -> AsyncIOMotorDatabase:
        """Get MongoDB database instance"""
        if self._db is None:
            raise RuntimeError("MongoDB not initialized")
        return self._db


class MongoDocuments(DocumentManager):
    """MongoDB implementation of document operations"""
    
    def __init__(self, parent: 'MongoDatabase'):
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
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            
            # Build aggregation pipeline
            pipeline = []
            
            # 1. Filter stage
            if filter:
                pipeline.append({"$match": self._build_query_filter(filter, entity_type)})
            
            # Use facet to get both data and count
            facet_pipeline: Dict[str, Any] = {
                "data": [],
                "count": [{"$count": "total"}]
            }
            
            # 2. Sort stage - get from metadata if not provided
            sort_spec = self._build_sort_spec(sort, entity_type)
            if sort_spec:
                facet_pipeline["data"].append({"$sort": sort_spec})
            
            # 3. Pagination stage
            skip_count = (page - 1) * pageSize
            facet_pipeline["data"].extend([
                {"$skip": skip_count},
                {"$limit": pageSize}
            ])
            
            pipeline.append({"$facet": facet_pipeline})
            
            # Execute query with case-insensitive collation if configured
            collation = None
            if not self.parent.case_sensitive_sorting:
                collation = {"locale": "en", "strength": 2}
                
            cursor = db[collection].aggregate(pipeline, collation=collation)
            result = await cursor.to_list(1)
            
            if not result:
                return [], 0
            
            facet_result = result[0]
            raw_data = facet_result.get("data", [])
            count_result = facet_result.get("count", [])
            total_count = count_result[0]["total"] if count_result else 0
            
            # Normalize IDs and prepare documents
            documents = []
            for doc in raw_data:
                doc = self._normalize_document(doc)
                documents.append(doc)
            
            # Note: FK processing handled in model layer based on config/view specs
            # Database returns raw documents only
            
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
        entity_type: str,
        # process_fks: bool = True,
        # view_spec: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            
            # Convert string ID to ObjectId for MongoDB
            try:
                object_id = ObjectId(id) if ObjectId.is_valid(id) else id
            except:
                object_id = id
            
            doc = await db[collection].find_one({"_id": object_id})
            
            if doc:
                # Normalize ID and return document
                doc = self._normalize_document(doc)
                return doc, 1
            else:
                not_found_warning(f"Document not found", entity=entity_type, entity_id=id)
                return {}, 0
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="get"
            )
    
    async def _validate_document_exists_for_update(self, entity_type: str, id: str) -> bool:
        """Validate that document exists for update operations"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            mongo_id = ObjectId(id) if ObjectId.is_valid(id) else id
            existing_doc = await db[collection].find_one({"_id": mongo_id})
            
            if not existing_doc:
                from app.services.notification import not_found_warning
                not_found_warning(f"Document not found for update", entity=entity_type, entity_id=id)
                return False
            
            return True
        except Exception:
            from app.services.notification import not_found_warning
            not_found_warning(f"Document not found for update", entity=entity_type, entity_id=id)
            return False
    
    async def _create_document(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in MongoDB. If data contains 'id', use it as _id, otherwise auto-generate."""
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            create_data = data.copy()
            
            # If data contains 'id', use it as MongoDB _id
            if 'id' in create_data:
                create_data["_id"] = create_data.pop('id')
            
            result = await db[collection].insert_one(create_data)
            saved_doc = create_data.copy()
            if "_id" not in saved_doc:
                saved_doc["_id"] = result.inserted_id
            return saved_doc
            
        except DuplicateKeyError as e:
            # Convert MongoDB duplicate key error to database-agnostic exception
            field, value = self._parse_duplicate_key_error(e)
            from app.errors import DuplicateConstraintError
            raise DuplicateConstraintError(
                message=f"Duplicate value for field '{field}'",
                entity=entity_type,
                field=field,
                entity_id=data.get('id', 'new')
            )
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="create"
            )

    async def _update_document(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing document in MongoDB. Extracts id from data['id']."""
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            id = data['id']  # Extract id from data
            mongo_id = ObjectId(id) if ObjectId.is_valid(id) else id
            
            # Create update data without 'id' field
            update_data = data.copy()
            del update_data['id']
            update_data["_id"] = mongo_id
            
            await db[collection].replace_one(
                {"_id": mongo_id}, 
                update_data,
                upsert=False
            )
            return update_data
                
        except DuplicateKeyError as e:
            # Convert MongoDB duplicate key error to database-agnostic exception
            field, value = self._parse_duplicate_key_error(e)
            from app.errors import DuplicateConstraintError
            raise DuplicateConstraintError(
                message=f"Duplicate value for field '{field}'",
                entity=entity_type,
                field=field,
                entity_id=data.get('id', 'new')
            )
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="save"
            )
    
    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance"""
        return self.parent.core
    
    async def delete(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID using atomic findOneAndDelete"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            
            # Convert string ID to ObjectId for MongoDB
            try:
                object_id = ObjectId(id) if ObjectId.is_valid(id) else id
            except:
                object_id = id
            
            # Use findOneAndDelete for atomic operation that returns deleted document
            deleted_doc = await db[collection].find_one_and_delete({"_id": object_id})
            
            if deleted_doc:
                # Normalize the deleted document and return
                normalized_doc = self._normalize_document(deleted_doc)
                return normalized_doc, 1
            else:
                not_found_warning(f"Document not found for deletion", entity=entity_type, entity_id=id)
                return {}, 0
            
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="delete"
            )
    
    # Database-specific implementation methods
    def _prepare_datetime_fields(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for MongoDB storage (string -> datetime objects)"""
        
        fields_meta = MetadataService.fields(entity_type)
        prepared_data = data.copy()
        
        for field_name, value in prepared_data.items():
            if value is None:
                continue
                
            field_meta = fields_meta.get(field_name, {})
            field_type = field_meta.get('type')
            
            if field_type in ['Date', 'Datetime'] and isinstance(value, str):
                try:
                    # Convert ISO string to datetime object for MongoDB
                    date_str = value.strip()
                    if date_str.endswith('Z'):
                        date_str = date_str[:-1] + '+00:00'
                    prepared_data[field_name] = datetime.fromisoformat(date_str)
                except (ValueError, TypeError):
                    # Leave as-is if conversion fails
                    pass
        
        return prepared_data
    
    async def _validate_unique_constraints(
        self, 
        entity_type: str, 
        data: Dict[str, Any], 
        unique_constraints: List[List[str]], 
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints for MongoDB (uses native indexes)"""
        # MongoDB handles unique constraints natively through indexes
        # The database will throw DuplicateKeyError on save if constraints are violated
        # We could do pre-validation here, but it's not necessary since MongoDB handles it
        # and adds a race condition. Let MongoDB handle it natively.
        return True  # Always return success, let native constraints handle violations
    
    def _build_query_filter(self, filters: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Build MongoDB query from filter conditions"""
        if not filters:
            return {}
        
        fields_meta = MetadataService.fields(entity_type)

        query: Dict[str, Any] = {}
        for field, value in filters.items():
            
            if isinstance(value, dict) and any(op in value for op in ['$gte', '$lte', '$gt', '$lt']):
                # Range query - add null exclusion for numeric/date fields
                field_type = fields_meta.get(field, {}).get('type', 'String')
                if field_type in ['Date', 'Datetime', 'Integer', 'Currency', 'Float']:
                    enhanced_filter = value.copy()
                    enhanced_filter['$exists'] = True
                    enhanced_filter['$ne'] = None
                    query[field] = enhanced_filter
                else:
                    query[field] = value
            else:
                # Determine matching strategy based on field type
                field_type = fields_meta.get(field, {}).get('type', 'String')
                if field_type == 'String':
                    # Text fields: partial match with regex (case-insensitive)
                    query[field] = {"$regex": f".*{self._escape_regex(str(value))}.*", "$options": "i"}
                else:
                    # Non-text fields: exact match
                    if isinstance(value, str) and ObjectId.is_valid(value):
                        query[field] = ObjectId(value)
                    else:
                        query[field] = value
        
        return query
    
    def _build_sort_spec(self, sort_fields: Optional[List[Tuple[str, str]]], entity_type: str) -> Dict[str, int]:
        """Build MongoDB sort specification"""
        if sort_fields:
            sort_spec = {}
            for field, direction in sort_fields:
                sort_spec[field] = 1 if direction == "asc" else -1
            return sort_spec
        else:
            return {self.parent.core._get_default_sort_field(entity_type): 1}  # Fallback to ID ascending
    
    def _parse_duplicate_key_error(self, error: DuplicateKeyError) -> Tuple[str, str]:
        """Parse MongoDB duplicate key error to extract field and value"""
        # Simplified parsing - could be improved with better error message parsing
        error_msg = str(error)
        # Try to extract field name from error message
        if "index:" in error_msg:
            # Example: "E11000 duplicate key error collection: db.users index: email_1"
            parts = error_msg.split("index:")
            if len(parts) > 1:
                index_info = parts[1].strip()
                field_name = index_info.split("_")[0]  # Extract field before _1
                return field_name, "unknown_value"
        
        return "unknown_field", "unknown_value"
    
    def _escape_regex(self, text: str) -> str:
        """Escape special regex characters"""
        import re
        return re.escape(text)


class MongoEntities(EntityManager):
    """MongoDB implementation of entity operations"""
    
    def __init__(self, parent: 'MongoDatabase'):
        self.parent = parent
    
    async def exists(self, entity_type: str) -> bool:
        """Check if collection exists"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        collection_names = await db.list_collection_names()
        return entity_type in collection_names
    
    async def create(self, entity_type: str, unique_constraints: List[List[str]]) -> bool:
        """Create collection with unique indexes"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            # MongoDB creates collections implicitly, but we can create indexes
            for constraint_fields in unique_constraints:
                index_spec = [(field, 1) for field in constraint_fields]
                await db[entity_type].create_index(index_spec, unique=True)
            
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="create"
            )
    
    async def delete(self, entity_type: str) -> bool:
        """Drop collection"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            await db[entity_type].drop()
            return True
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="delete"
            )
    
    async def get_all(self) -> List[str]:
        """Get all collection names"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        return await db.list_collection_names()


class MongoIndexes(IndexManager):
    """MongoDB implementation of index operations"""
    
    def __init__(self, parent: 'MongoDatabase'):
        self.parent = parent
    
    async def create(
        self, 
        entity_type: str, 
        fields: List[str],
        unique: bool = False,
        name: Optional[str] = None
    ) -> None:
        """Create index on collection"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            index_spec = [(field, 1) for field in fields]
            kwargs: Dict[str, Any] = {"unique": unique}
            if name:
                kwargs["name"] = name
                
            await db[entity_type].create_index(index_spec, **kwargs)
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="create_index"
            )
    
    async def get_all(self, entity_type: str) -> List[List[str]]:
        """Get all unique indexes for collection as field lists"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            field_lists = []
            cursor = db[entity_type].list_indexes()
            
            async for index_info in cursor:
                # Skip system indexes like _id_
                if index_info.get("name") == "_id_":
                    continue
                    
                # Only include unique indexes
                if not index_info.get("unique", False):
                    continue
                
                # Extract field names from MongoDB key structure
                fields = []
                for field_spec in index_info.get("key", {}).items():
                    fields.append(field_spec[0])
                
                if fields:  # Only add if we have fields
                    field_lists.append(fields)
            
            return field_lists
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="list_indexes"
            )
    
    async def delete(self, entity_type: str, fields: List[str]) -> None:
        """Delete index by field names"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            # Use MongoDB's drop_index with field specification
            # MongoDB can drop index by field specification: [(field, direction), ...]
            index_spec = [(field, 1) for field in fields]
            await db[entity_type].drop_index(index_spec)
        except Exception as e:
            raise DatabaseError(
                message=str(e),
                entity=entity_type,
                operation="delete_index"
            )


class MongoDatabase(DatabaseInterface):
    """MongoDB implementation of DatabaseInterface"""
    
    def _create_core_manager(self) -> CoreManager:
        return MongoCore(self)
    
    def _create_document_manager(self) -> DocumentManager:
        return MongoDocuments(self)
    
    def _create_entity_manager(self) -> EntityManager:
        return MongoEntities(self)
    
    def _create_index_manager(self) -> IndexManager:
        return MongoIndexes(self)
    
    async def supports_native_indexes(self) -> bool:
        """MongoDB supports native unique indexes"""
        return True