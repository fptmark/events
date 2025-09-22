"""
MongoDB document operations implementation.
Contains the MongoDocuments class with CRUD operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from ..document_manager import DocumentManager
from ..core_manager import CoreManager
from app.services.notify import Notification, Warning, Error, DuplicateConstraintError
from app.services.metadata import MetadataService


class MongoDocuments(DocumentManager):
    """MongoDB implementation of document operations"""
    
    def __init__(self, parent):
        self.parent = parent

    def isInternallyCaseSensitive(self) -> bool:
        """MongoDB is case-sensitive for field names"""
        return True
    
    async def _get_all_impl(
        self,
        entity_type: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated list of documents"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        collection = entity_type
        
        # Build query filter
        query = self._build_query_filter(filter, entity_type) if filter else {}
        
        # Get total count
        total_count = await db[collection].count_documents(query)
        
        # Build sort specification
        sort_spec = self._build_sort_spec(sort, entity_type)
        
        # Execute paginated query
        skip_count = (page - 1) * pageSize
        cursor = db[collection].find(query).sort(sort_spec).skip(skip_count).limit(pageSize)
        
        # Apply case-insensitive collation if configured
        if not self.parent.case_sensitive_sorting:
            cursor = cursor.collation({"locale": "en", "strength": 2})
        
        raw_documents = await cursor.to_list(length=pageSize)
        
        # Normalize documents
        documents = [self._normalize_document(doc) for doc in raw_documents]
        
        return documents, total_count
    
    async def _get_impl(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            
            # Convert string ID to ObjectId for MongoDB
            # But it only works as a string.  Strange but true!
            # object_id = ObjectId(id) if ObjectId.is_valid(id) else id
            
            doc = await db[collection].find_one({"_id": id})
            
            if doc:
                normalized_doc = self._normalize_document(doc)
                return normalized_doc, 1
            else:
                Notification.warning(Warning.NOT_FOUND, "Document not found", entity_type=entity_type, entity_id=id)
                return {}, 0
            
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB get error: {str(e)}")

        return {}, 0

    async def _delete_impl(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            
            # Use findOneAndDelete for atomic operation that returns deleted document
            deleted_doc = await db[collection].find_one_and_delete({"_id": id})
            
            if deleted_doc:
                normalized_doc = self._normalize_document(deleted_doc)
                return normalized_doc, 1
            else:
                Notification.warning(Warning.NOT_FOUND, "Document not found for deletion", entity_type=entity_type, entity_id=id)
                return {}, 0
            
        except Exception as e:
            Notification.error(Error.DATABASE, f"MongoDB delete error: {str(e)}")

        return {}, 0
    
    async def _validate_document_exists_for_update(self, entity_type: str, id: str) -> bool:
        """Validate that document exists for update operations"""
        self.parent._ensure_initialized()
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            mongo_id = ObjectId(id) if ObjectId.is_valid(id) else id
            existing_doc = await db[collection].find_one({"_id": mongo_id})
            
            if not existing_doc:
                Notification.warning(Warning.NOT_FOUND, "Document not found for update", entity_type=entity_type, entity_id=id)
                return False
            
            return True
        except Exception:
            Notification.warning(Warning.NOT_FOUND, "Document not found for update", entity_type=entity_type, entity_id=id)
            return False
    
    async def _create_impl(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in MongoDB"""
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            
            # If data contains 'id', use it as MongoDB _id
            if 'id' in data and data['id']:
                data["_id"] = data.pop('id')
            
            result = await db[collection].insert_one(data)
            if "_id" in data:
                data["id"] = result.inserted_id
            else:
                Notification.error(Error.DATABASE, "MongoDB insert error: {result}")
            return data
            
        except DuplicateKeyError as e:
            field, value = self._parse_duplicate_key_error(e)
            error = DuplicateConstraintError(
                message=f"Duplicate value for field '{field}'",
                entity=entity_type,
                field=field,
                entity_id=data.get('id', 'new')
            )
            Notification.handle_duplicate_constraint(error)

        return {}

    async def _update_impl(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing document in MongoDB"""
        db = self.parent.core.get_connection()
        
        try:
            collection = entity_type
            # If data contains 'id', use it as MongoDB _id ... and it better.
            if 'id' in data and data['id']:
                data["_id"] = data.pop('id')
            
            await db[collection].replace_one({"_id": id}, data, upsert=False)
            return data
                
        except DuplicateKeyError as e:
            field, value = self._parse_duplicate_key_error(e)
            error = DuplicateConstraintError(
                message=f"Duplicate value for field '{field}'",
                entity=entity_type,
                field=field,
                entity_id=data.get('id', 'new')
            )
            Notification.handle_duplicate_constraint(error)
    
        return {}

    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance"""
        return self.parent.core
    
    def _prepare_datetime_fields(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for MongoDB storage"""
        fields_meta = MetadataService.fields(entity_type)
        prepared_data = data.copy()
        
        for field_name, value in prepared_data.items():
            if value is None:
                continue
                
            field_meta = fields_meta.get(field_name, {})
            field_type = field_meta.get('type')
            
            if field_type in ['Date', 'Datetime'] and isinstance(value, str):
                try:
                    date_str = value.strip()
                    if date_str.endswith('Z'):
                        date_str = date_str[:-1] + '+00:00'
                    prepared_data[field_name] = datetime.fromisoformat(date_str)
                except (ValueError, TypeError):
                    pass
        
        return prepared_data
    
    def _convert_filter_values(self, filters: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Convert filter values to MongoDB-appropriate types"""
        if not filters:
            return filters
            
        converted_filters = {}
        fields_meta = MetadataService.fields(entity_type)
        
        for field_name, filter_value in filters.items():
            field_meta = fields_meta.get(field_name, {})
            field_type = field_meta.get('type', 'String')
            
            if isinstance(filter_value, dict):
                # Range queries like {"$gte": 21, "$lt": 65}
                converted_range = {}
                for op, value in filter_value.items():
                    converted_range[op] = self._convert_single_value(value, field_type)
                converted_filters[field_name] = converted_range
            else:
                # Simple equality filter
                converted_filters[field_name] = self._convert_single_value(filter_value, field_type)
        
        return converted_filters
    
    def _convert_single_value(self, value: Any, field_type: str) -> Any:
        """Convert a single value to appropriate type for MongoDB"""
        if value is None:
            return value
            
        if field_type in ['Date', 'Datetime'] and isinstance(value, str):
            try:
                date_str = value.strip()
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                return datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                return value
        
        return value
    
    async def _validate_unique_constraints(
        self, 
        entity_type: str, 
        data: Dict[str, Any], 
        unique_constraints: List[List[str]], 
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints for MongoDB"""
        return True  # MongoDB handles unique constraints natively
    
    def _build_query_filter(self, filters: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Build MongoDB query from filter conditions"""
        if not filters:
            return {}
        
        converted_filters = self._convert_filter_values(filters, entity_type)
        fields_meta = MetadataService.fields(entity_type)
        query: Dict[str, Any] = {}
        
        for field, value in converted_filters.items():
            if isinstance(value, dict) and any(op in value for op in ['$gte', '$lte', '$gt', '$lt']):
                # Range query
                field_type = fields_meta.get(field, {}).get('type', 'String')
                if field_type in ['Date', 'Datetime', 'Integer', 'Currency', 'Float']:
                    enhanced_filter = value.copy()
                    enhanced_filter['$exists'] = True
                    enhanced_filter['$ne'] = None
                    query[field] = enhanced_filter
                else:
                    query[field] = value
            else:
                # Determine matching strategy
                field_meta = fields_meta.get(field, {})
                field_type = field_meta.get('type', 'String')
                has_enum_values = 'enum' in field_meta
                
                if field_type == 'String' and not has_enum_values:
                    # Free text fields: partial match with regex
                    query[field] = {"$regex": f".*{self._escape_regex(str(value))}.*", "$options": "i"}
                else:
                    # Enum fields and non-text fields: exact match
                    if isinstance(value, str) and ObjectId.is_valid(value):
                        query[field] = ObjectId(value)
                    else:
                        query[field] = value
        
        return query
    
    def _build_sort_spec(self, sort_fields: Optional[List[Tuple[str, str]]], entity_type: str) -> List[Tuple[str, int]]:
        """Build MongoDB sort specification"""
        if sort_fields:
            return [(field, 1 if direction == "asc" else -1) for field, direction in sort_fields]
        else:
            return [("_id", 1)]  # Default sort by _id ascending
    
    def _parse_duplicate_key_error(self, error: DuplicateKeyError) -> Tuple[str, str]:
        """Parse MongoDB duplicate key error to extract field and value"""
        error_msg = str(error)
        if "index:" in error_msg:
            parts = error_msg.split("index:")
            if len(parts) > 1:
                index_info = parts[1].strip()
                field_name = index_info.split("_")[0]
                return field_name, "unknown_value"
        return "unknown_field", "unknown_value"
    
    def _escape_regex(self, text: str) -> str:
        """Escape special regex characters"""
        import re
        return re.escape(text)