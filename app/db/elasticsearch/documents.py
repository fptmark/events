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
from app.exceptions import DocumentNotFound, DatabaseError, DuplicateConstraintError
from app.services.metadata import MetadataService
from app.services.notify import Notification
from app.services.request_context import RequestContext
from app.config import Config


class ElasticsearchDocuments(DocumentManager):
    """Elasticsearch implementation of document operations"""
    
    def __init__(self, database):
        super().__init__(database)

    def _get_proper_sort_fields(self, sort_fields: Optional[List[Tuple[str, str]]], entity: str) -> Optional[List[Tuple[str, str]]]:
        """Get sort fields with proper case names"""
        if not sort_fields:
            return sort_fields

        proper_sort = []
        for field, direction in sort_fields:
            proper_field = MetadataService.get_proper_name(entity, field)
            proper_sort.append((proper_field, direction))
        return proper_sort

    def _get_proper_filter_fields(self, filters: Optional[Dict[str, Any]], entity: str) -> Optional[Dict[str, Any]]:
        """Get filter dict with proper case field names"""
        if not filters:
            return filters

        proper_filters = {}
        for field, value in filters.items():
            proper_field = MetadataService.get_proper_name(entity, field)
            # Value is preserved as-is (operators like $gte, $lt, etc. are MongoDB-specific, not field names)
            proper_filters[proper_field] = value
        return proper_filters

    def _get_proper_view_fields(self, view_spec: Dict[str, Any], entity: str) -> Dict[str, Any]:
        """Get view spec with proper case field names"""
        if not view_spec:
            return view_spec

        proper_view_spec = {}
        for fk_entity_name, field_list in view_spec.items():
            # Convert the foreign entity name to proper case
            proper_fk_entity_name = MetadataService.get_proper_name(fk_entity_name)

            # Convert each field name in the field list to proper case
            proper_field_list = []
            for field in field_list:
                proper_field = MetadataService.get_proper_name(fk_entity_name, field)
                proper_field_list.append(proper_field)

            proper_view_spec[proper_fk_entity_name] = proper_field_list

        return proper_view_spec
    
    async def _get_all_impl(
        self,
        entity: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated list of documents"""
        self.database._ensure_initialized()
        es = self.database.core.get_connection()

        # Convert entity to lowercase for ES index names
        index_name = entity.lower()

        if not await es.indices.exists(index=index_name):
            return [], 0

        # Convert field names to proper case using metadata
        proper_sort = self._get_proper_sort_fields(sort, entity)
        proper_filter = self._get_proper_filter_fields(filter, entity)

        # Build query
        query_body = {
            "from": (page - 1) * pageSize,
            "size": pageSize,
            "query": self._build_query_filter(proper_filter, entity)
        }

        # Add sorting (only if sort spec is not empty)
        sort_spec = self._build_sort_spec(proper_sort, entity)
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
        entity: str,
    ) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID"""
        self.database._ensure_initialized()
        es = self.database.core.get_connection()

        index = entity.lower()

        if not await es.indices.exists(index=index):
            raise DocumentNotFound(None, f"Index {index} does not exist")

        try:
            response = await es.get(index=index, id=id)
            # doc = self._normalize_document(response["_source"])
            return response["_source"], 1
        except NotFoundError as e:
            raise DocumentNotFound(e)
    
    async def _delete_impl(self, id: str, entity: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID"""
        self.database._ensure_initialized()
        es = self.database.core.get_connection()

        index = entity.lower()

        if not await es.indices.exists(index=index):
            return {}, 0

        # Elasticsearch doesn't return deleted doc automatically, so fetch it first
        try:
            # Get document before deleting
            doc = await es.get(index=index, id=id)

            # Delete with optional refresh for consistency
            # This ensures deleted documents are immediately removed from search results,
            # preventing false duplicate errors when re-creating with same unique values
            refresh_mode = 'wait_for' if (Config.elasticsearch_strict_consistency() and not RequestContext.no_consistency) else False
            delete_response = await es.delete(index=index, id=id, refresh=refresh_mode)
            if delete_response.get("result") == "deleted":
                return doc, 1
            else:
                raise DatabaseError(f"Elasticsearch delete returned unexpected result: {delete_response.get('result')}")

        except NotFoundError:
            # ES driver exception → translate to our app exception
            raise DocumentNotFound(entity, id)
        except Exception as e:
            raise DatabaseError(f"Elasticsearch delete error: {str(e)}")
    
    async def _create_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in Elasticsearch. If data contains 'id', use it as _id, otherwise auto-generate."""
        es = self.database.core.get_connection()

        index = entity.lower()
        create_data = data.copy()

        # If an 'id' was specified, use it as Elasticsearch _id
        if not id:
            id = str(uuid.uuid4())

        # Store shadow id field for sorting (not _id - that's metadata)
        create_data['id'] = id

        # Use refresh='wait_for' if strict consistency is enabled (default)
        # This ensures document is searchable immediately, which is critical for
        # duplicate constraint validation to work correctly with concurrent requests.
        # Can be disabled via:
        #   1. elasticsearch_strict_consistency=false config (global)
        #   2. ?no_consistency=true query param (per-request, for bulk loads)
        refresh_mode = 'wait_for' if (Config.elasticsearch_strict_consistency() and not RequestContext.no_consistency) else False
        await es.index(index=index, id=id, body=create_data, refresh=refresh_mode)

        return create_data

    async def _update_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        # update is the same as create in ES - it will upsert
        return await self._create_impl(entity, id, data)
    
    def _get_core_manager(self) -> CoreManager:
        """Get the core manager instance"""
        return self.database.core
    
    def _build_query_filter(self, filters: Optional[Dict[str, Any]], entity: str) -> Dict[str, Any]:
        """Build Elasticsearch query from filter conditions"""
        if not filters:
            return {"match_all": {}}

        must_clauses = []
        fields_meta = MetadataService.fields(entity)

        for field, value in filters.items():
            if isinstance(value, dict) and any(op in value for op in ['$gte', '$lte', '$gt', '$lt']):
                # Range query
                range_query = {}
                for op, val in value.items():
                    es_op = op.replace('$', '')  # $gte -> gte
                    range_query[es_op] = val
                must_clauses.append({"range": {field: range_query}})
            else:
                # Check field metadata to determine match strategy
                field_meta = fields_meta.get(field, {})
                field_type = field_meta.get('type', 'String')
                has_enum_values = 'enum' in field_meta

                if field_type == 'String' and not has_enum_values:
                    # Non-enum strings: substring match (anywhere in string)
                    # Lowercase value since fields use lc normalizer
                    value_lower = str(value).lower()
                    must_clauses.append({"wildcard": {field: f"*{value_lower}*"}})
                else:
                    # Enum fields and non-strings: exact match
                    must_clauses.append({"term": {field: value}})

        return {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}
    
    def _build_sort_spec(self, sort_fields: Optional[List[Tuple[str, str]]], entity: str) -> List[Dict[str, Any]]:
        """Build Elasticsearch sort specification

        If no sort specified, default to sorting by 'id' field (ascending) to ensure
        consistent ordering across pagination. Without this, ES uses internal _id which
        can result in inconsistent ordering.
        """
        if not sort_fields:
            # Default sort by 'id' field for consistent pagination
            return [{"id": {"order": "asc"}}]

        sort_spec = []
        for field, direction in sort_fields:
            sort_spec.append({field: {"order": direction}})

        return sort_spec
    
    def _prepare_datetime_fields(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for Elasticsearch storage (as ISO strings)"""
        from datetime import datetime
        
        fields_meta = MetadataService.fields(entity)
        data_copy = data.copy()
        
        for field, field_meta in fields_meta.items():
            if field in data_copy and field_meta.get('type') == 'DateTime':
                value = data_copy[field]
                if isinstance(value, datetime):
                    # Convert datetime to ISO string for ES storage
                    data_copy[field] = value.isoformat()
        
        return data_copy
    
    def _convert_filter_values(self, filters: Dict[str, Any], entity: str) -> Dict[str, Any]:
        """Convert filter values to Elasticsearch-appropriate types"""
        if not filters:
            return filters
            
        converted_filters = {}
        fields_meta = MetadataService.fields(entity)
        
        for field, filter_value in filters.items():
            field_meta = fields_meta.get(field, {})
            field_type = field_meta.get('type', 'String')
            
            if isinstance(filter_value, dict):
                # Range queries like {"$gte": 21, "$lt": 65}
                converted_range = {}
                for op, value in filter_value.items():
                    converted_range[op] = self._convert_single_value(value, field_type)
                converted_filters[field] = converted_range
            else:
                # Simple equality filter
                converted_filters[field] = self._convert_single_value(filter_value, field_type)
        
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
        entity: str,
        data: Dict[str, Any],
        unique_constraints: List[List[str]],
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints (Elasticsearch synthetic implementation)

        With the new keyword+lc normalizer template, string fields are keyword type
        with case-insensitive matching via the lc normalizer. We query them directly
        without needing .raw subfields.
        """

        if not unique_constraints:
            return True

        es = self.database.core.get_connection()
        index = entity.lower()

        if not await es.indices.exists(index=index):
            return True  # No existing docs to check against

        for constraint_fields in unique_constraints:
            # Build query to check for existing documents with same field values
            must_clauses = []
            for field in constraint_fields:
                if field in data and data[field] is not None:
                    # With keyword+lc normalizer, all string fields are keyword type
                    # The lc normalizer handles case-insensitive matching automatically
                    # Just use term query on the field directly
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
                    entity=entity,
                    field=duplicate_field,
                    entity_id=exclude_id or "new"
                )
                Notification.handle_duplicate_constraint(error)
                # Execution never reaches here - StopWorkError raised above

        return True