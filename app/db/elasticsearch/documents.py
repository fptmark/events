"""
Elasticsearch document operations implementation.
Contains the ElasticsearchDocuments class with CRUD operations.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from elasticsearch.exceptions import NotFoundError

from ..document_manager import DocumentManager
from ..core_manager import CoreManager
from ..exceptions import DocumentNotFound, DatabaseError
from app.services.notify import Notification, Warning, Error, DuplicateConstraintError
from app.services.metadata import MetadataService


class ElasticsearchDocuments(DocumentManager):
    """Elasticsearch implementation of document operations"""
    
    def __init__(self, database):
        super().__init__(database)

    def _get_proper_sort_fields(self, sort_fields: Optional[List[Tuple[str, str]]], entity_type: str) -> Optional[List[Tuple[str, str]]]:
        """Get sort fields with proper case names"""
        if not sort_fields:
            return sort_fields

        proper_sort = []
        for field_name, direction in sort_fields:
            proper_field_name = MetadataService.get_proper_name(entity_type, field_name)
            proper_sort.append((proper_field_name, direction))
        return proper_sort

    def _get_proper_filter_fields(self, filters: Optional[Dict[str, Any]], entity_type: str) -> Optional[Dict[str, Any]]:
        """Get filter dict with proper case field names"""
        if not filters:
            return filters

        proper_filters = {}
        for field_name, value in filters.items():
            proper_field_name = MetadataService.get_proper_name(entity_type, field_name)
            # Value is preserved as-is (operators like $gte, $lt, etc. are MongoDB-specific, not field names)
            proper_filters[proper_field_name] = value
        return proper_filters

    def _get_proper_view_fields(self, view_spec: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Get view spec with proper case field names"""
        if not view_spec:
            return view_spec

        proper_view_spec = {}
        for fk_entity_name, field_list in view_spec.items():
            # Convert the foreign entity name to proper case
            proper_fk_entity_name = MetadataService.get_proper_name(fk_entity_name)

            # Convert each field name in the field list to proper case
            proper_field_list = []
            for field_name in field_list:
                proper_field_name = MetadataService.get_proper_name(fk_entity_name, field_name)
                proper_field_list.append(proper_field_name)

            proper_view_spec[proper_fk_entity_name] = proper_field_list

        return proper_view_spec
    
    async def _get_all_impl(
        self,
        entity_type: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated list of documents"""
        self.database._ensure_initialized()
        es = self.database.core.get_connection()

        # Convert entity_type to lowercase for ES index names
        index_name = entity_type.lower()

        if not await es.indices.exists(index=index_name):
            return [], 0

        # Convert field names to proper case using metadata
        proper_sort = self._get_proper_sort_fields(sort, entity_type)
        proper_filter = self._get_proper_filter_fields(filter, entity_type)

        # Build query
        query_body = {
            "from": (page - 1) * pageSize,
            "size": pageSize,
            "query": self._build_query_filter(proper_filter, entity_type)
        }

        # Add sorting (only if sort spec is not empty)
        sort_spec = self._build_sort_spec(proper_sort, entity_type)
        if sort_spec:
            query_body["sort"] = sort_spec

        # Execute query
        response = await es.search(index=index_name, body=query_body)
        hits = response.get("hits", {}).get("hits", [])

        documents = []
        for hit in hits:
            # doc = self._normalize_document(hit["_source"])
            documents.append(hit["_source"])

        total_count = response.get("hits", {}).get("total", {}).get("value", 0)

        return documents, total_count
    
    async def _get_impl(
        self,
        id: str,
        entity_type: str,
    ) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID"""
        self.database._ensure_initialized()
        es = self.database.core.get_connection()

        index = entity_type.lower()

        if not await es.indices.exists(index=index):
            raise DocumentNotFound(None, f"Index {index} does not exist")

        try:
            response = await es.get(index=index, id=id)
            # doc = self._normalize_document(response["_source"])
            return response["_source"], 1
        except NotFoundError as e:
            raise DocumentNotFound(e)
    
    async def _delete_impl(self, id: str, entity_type: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID"""
        self.database._ensure_initialized()
        es = self.database.core.get_connection()

        index = entity_type.lower()

        if not await es.indices.exists(index=index):
            return {}, 0

        # Elasticsearch doesn't return deleted doc automatically, so fetch it first
        try:
            # Get document before deleting
            doc = await es.get(index=index, id=id)
            # doc = self._normalize_document(get_response["_source"])

            # Now delete it
            delete_response = await es.delete(index=index, id=id)
            if delete_response.get("result") == "deleted":
                return doc, 1
            else:
                return {}, 0
        except Exception as e:
            if "not found" not in str(e).lower():
                Notification.error(Error.DATABASE, f"Elasticsearch delete error: {str(e)}")
            return {}, 0
    
    async def _create_impl(self, entity_type: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in Elasticsearch. If data contains 'id', use it as _id, otherwise auto-generate."""
        es = self.database.core.get_connection()

        index = entity_type.lower()
        create_data = data.copy()

        # If an 'id' was specified, use it as Elasticsearch _id
        if not id:
            id = str(uuid.uuid4())

        # Store shadow id field for sorting (not _id - that's metadata)
        create_data['id'] = id

        await es.index(index=index, id=id, body=create_data)

        return create_data

    async def _update_impl(self, entity_type: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        # update is the same as create in ES - it will upsert
        return await self._create_impl(entity_type, id, data)
    
    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance"""
        return self.database.core
    
    def _build_query_filter(self, filters: Optional[Dict[str, Any]], entity_type: str) -> Dict[str, Any]:
        """Build Elasticsearch query from filter conditions"""
        if not filters:
            return {"match_all": {}}
        
        must_clauses = []
        for field, value in filters.items():
            if isinstance(value, dict) and any(op in value for op in ['$gte', '$lte', '$gt', '$lt']):
                # Range query
                range_query = {}
                for op, val in value.items():
                    es_op = op.replace('$', '')  # $gte -> gte
                    range_query[es_op] = val
                must_clauses.append({"range": {field: range_query}})
            else:
                # Exact match
                must_clauses.append({"term": {field: value}})
        
        return {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
    
    def _build_sort_spec(self, sort_fields: Optional[List[Tuple[str, str]]], entity_type: str) -> List[Dict[str, Any]]:
        """Build Elasticsearch sort specification"""
        if not sort_fields:
            # No default sort - let Elasticsearch handle natural ordering
            return []  
        
        sort_spec = []
        for field, direction in sort_fields:
            sort_spec.append({field: {"order": direction}})
        
        return sort_spec
    
    def _prepare_datetime_fields(self, entity_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for Elasticsearch storage (as ISO strings)"""
        from datetime import datetime
        
        fields_meta = MetadataService.fields(entity_type)
        data_copy = data.copy()
        
        for field_name, field_meta in fields_meta.items():
            if field_name in data_copy and field_meta.get('type') == 'DateTime':
                value = data_copy[field_name]
                if isinstance(value, datetime):
                    # Convert datetime to ISO string for ES storage
                    data_copy[field_name] = value.isoformat()
        
        return data_copy
    
    def _convert_filter_values(self, filters: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Convert filter values to Elasticsearch-appropriate types"""
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
    
    def _convert_single_value(self, value, field_type: str):
        """Convert a single filter value based on field type"""
        if field_type in ('Date', 'DateTime'):
            # For date fields, ensure string format for ES
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            return str(value)
        elif field_type == 'Boolean':
            # Convert boolean strings to actual booleans
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        elif field_type in ('Number', 'Currency', 'Integer'):
            # Ensure numeric types
            try:
                return float(value) if field_type in ('Number', 'Currency') else int(value)
            except (ValueError, TypeError):
                return value
        else:
            # String and other types - keep as-is
            return value
    
    async def _validate_unique_constraints(
        self, 
        entity_type: str, 
        data: Dict[str, Any], 
        unique_constraints: List[List[str]], 
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints (Elasticsearch synthetic implementation)"""
        
        # Get unique constraints from metadata if not provided
        if not unique_constraints:
            metadata = MetadataService.get(entity_type) 
            if metadata:
                unique_constraints = metadata.get('unique_constraints', [])
            else:
                Notification.warning(Warning.BAD_NAME, "Unknown entity", entity_type=entity_type)
                return False
        
        if not unique_constraints:
            return True
            
        es = self.database.core.get_connection()
        index = entity_type.lower()
        
        if not await es.indices.exists(index=index):
            return True  # No existing docs to check against
            
        for constraint_fields in unique_constraints:
            # Build query to check for existing documents with same field values
            must_clauses = []
            for field in constraint_fields:
                if field in data and data[field] is not None:
                    # Use .raw field for exact string matching if it's a text field
                    type = MetadataService.get(entity_type, field, 'type')
                    
                    if type == 'String':
                        # Use .raw subfield for exact matching on strings
                        must_clauses.append({"term": {f"{field}.raw": data[field]}})
                    else:
                        # Use direct field for non-string types
                        must_clauses.append({"term": {field: data[field]}})
            
            if not must_clauses:
                continue
                
            # Exclude current document if updating
            query = {"bool": {"must": must_clauses}}
            if exclude_id:
                query["bool"]["must_not"] = [{"term": {"_id": exclude_id}}]
            
            response = await es.search(
                index=index,
                body={"query": query, "size": 1}
            )
            
            if response.get("hits", {}).get("total", {}).get("value", 0) > 0:
                # Use first field in constraint (matches MongoDB pattern)
                duplicate_field = constraint_fields[0]
                
                error = DuplicateConstraintError(
                    message=f"Duplicate value for field '{duplicate_field}'",
                    entity=entity_type,
                    field=duplicate_field,
                    entity_id=exclude_id or "new"
                )
                Notification.handle_duplicate_constraint(error)
                # Execution never reaches here - StopWorkError raised above
        
        return True