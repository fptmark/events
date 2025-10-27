"""
PostgreSQL document operations - CRUD with JSONB storage.
"""

import asyncpg
import json
from typing import Any, Dict, List, Optional, Tuple

from ..document_manager import DocumentManager
from ..core_manager import CoreManager
from app.exceptions import DocumentNotFound, DatabaseError, DuplicateConstraintError
from app.services.metadata import MetadataService


class PostgreSQLDocuments(DocumentManager):
    """PostgreSQL implementation of document operations using JSONB storage"""

    def __init__(self, database):
        super().__init__(database)

    async def _create_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in PostgreSQL"""
        # Remove 'id' from data - stored in separate column
        data.pop('id', None)

        async with self.database.core.pool.acquire() as conn:
            # Ensure table exists
            await conn.execute(f'''
                CREATE TABLE IF NOT EXISTS "{entity}" (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL
                )
            ''')

            try:
                # Insert document (convert dict to JSON string)
                await conn.execute(
                    f'INSERT INTO "{entity}" (id, data) VALUES ($1, $2::jsonb)',
                    id, json.dumps(data)
                )
                # Return with 'id' for API response
                return {'id': id, **data}

            except asyncpg.UniqueViolationError as e:
                # Unique constraint violation
                raise DuplicateConstraintError(
                    message=f"Duplicate key error",
                    entity=entity,
                    field="id",
                    entity_id=id
                )
            except asyncpg.PostgresError as e:
                raise DatabaseError(f"PostgreSQL error: {str(e)}")

    async def _get_impl(self, entity: str, id: str) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID"""
        async with self.database.core.pool.acquire() as conn:
            row = await conn.fetchrow(
                f'SELECT id, data FROM "{entity}" WHERE id = $1',
                id
            )

            if not row:
                raise DocumentNotFound(entity, id)

            # Parse JSON string from JSONB column
            document = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
            document['id'] = row['id']
            return document, 1

    async def _get_all_impl(
        self,
        entity: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25,
        filter_matching: str = "contains"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated list of documents with filter/sort"""
        async with self.database.core.pool.acquire() as conn:
            # Build WHERE clause from filters
            where_parts = []
            params = []
            param_idx = 1

            if filter:
                fields_meta = MetadataService.fields(entity)
                for field, value in filter.items():
                    if isinstance(value, dict):
                        # Range queries: {$gte: 21, $lt: 65}
                        for op, val in value.items():
                            sql_op = self._mongo_operator_to_sql(op)
                            where_parts.append(
                                f"(data->>'{field}')::NUMERIC {sql_op} ${param_idx}"
                            )
                            params.append(val)
                            param_idx += 1
                    else:
                        # Check if this is an enum field or non-enum string
                        field_meta = fields_meta.get(field, {})
                        field_type = field_meta.get('type', 'String')
                        has_enum_values = 'enum' in field_meta

                        if field_type == 'String' and not has_enum_values:
                            if filter_matching == "exact":
                                # Exact match for auth and other exact-match use cases
                                where_parts.append(
                                    f"data->>'{field}' = ${param_idx}"
                                )
                                params.append(value)
                            else:
                                # Non-enum strings: substring match (case-insensitive with ILIKE)
                                where_parts.append(
                                    f"data->>'{field}' ILIKE ${param_idx}"
                                )
                                params.append(f"%{value}%")
                        else:
                            # Enum fields and non-strings: always exact match
                            where_parts.append(
                                f"data->>'{field}' = ${param_idx}"
                            )
                            params.append(value)

                        param_idx += 1

            where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

            # Build ORDER BY clause
            order_clause = ""
            if sort:
                fields_meta = MetadataService.fields(entity)
                order_parts = []
                for field, direction in sort:
                    # Convert field name to proper case (e.g., 'firstname' -> 'firstName')
                    proper_field = MetadataService.get_proper_name(entity, field)

                    # Special case: 'id' is stored in table column, not JSON
                    if proper_field == 'id':
                        if self.database.case_sensitive_sorting:
                            order_parts.append(f"id {direction.upper()}")
                        else:
                            order_parts.append(f"LOWER(id) {direction.upper()}")
                    else:
                        # Other fields are in JSONB - need type-aware casting
                        field_meta = fields_meta.get(proper_field, {})
                        field_type = field_meta.get('type', 'String')

                        # Cast to appropriate type for proper sorting
                        if field_type in ['Integer', 'Number', 'Currency', 'Float']:
                            # Numeric sorting
                            order_parts.append(f"(data->>'{proper_field}')::NUMERIC {direction.upper()}")
                        elif field_type in ['Date', 'Datetime']:
                            # Date/timestamp sorting
                            order_parts.append(f"(data->>'{proper_field}')::TIMESTAMP {direction.upper()}")
                        else:
                            # String sorting (with optional case-insensitive)
                            if self.database.case_sensitive_sorting:
                                order_parts.append(f"data->>'{proper_field}' {direction.upper()}")
                            else:
                                order_parts.append(f"LOWER(data->>'{proper_field}') {direction.upper()}")
                order_clause = f"ORDER BY {', '.join(order_parts)}"
            else:
                # Default sort by 'id' column for consistent pagination
                if self.database.case_sensitive_sorting:
                    order_clause = f"ORDER BY id ASC"
                else:
                    order_clause = f"ORDER BY LOWER(id) ASC"

            # Pagination
            offset = self._calculate_pagination_offset(page, pageSize)
            limit_clause = f"LIMIT ${param_idx} OFFSET ${param_idx + 1}"
            params.extend([pageSize, offset])

            # Execute main query
            query = f'''
                SELECT id, data FROM "{entity}"
                {where_clause}
                {order_clause}
                {limit_clause}
            '''

            rows = await conn.fetch(query, *params)

            # Get total count (without pagination)
            count_params = params[:-2]  # Exclude LIMIT/OFFSET params
            count_query = f'SELECT COUNT(*) FROM "{entity}" {where_clause}'
            total = await conn.fetchval(count_query, *count_params) if count_params else await conn.fetchval(count_query)

            # Parse JSONB documents
            documents = []
            for row in rows:
                doc = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
                doc['id'] = row['id']
                documents.append(doc)

            return documents, total

    async def _update_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing document"""
        # Remove 'id' from data - stored in separate column
        data.pop('id', None)

        async with self.database.core.pool.acquire() as conn:
            try:
                result = await conn.execute(
                    f'UPDATE "{entity}" SET data = $1::jsonb WHERE id = $2',
                    json.dumps(data), id
                )

                # asyncpg returns "UPDATE N" where N is row count
                if result == "UPDATE 0":
                    raise DocumentNotFound(entity, id)

                # Return with 'id' for API response
                return {'id': id, **data}

            except asyncpg.UniqueViolationError as e:
                raise DuplicateConstraintError(
                    message=f"Duplicate key error on update",
                    entity=entity,
                    field="unknown",
                    entity_id=id
                )
            except asyncpg.PostgresError as e:
                raise DatabaseError(f"PostgreSQL error: {str(e)}")

    async def _delete_impl(self, entity: str, id: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID"""
        async with self.database.core.pool.acquire() as conn:
            # Fetch document before deleting
            row = await conn.fetchrow(
                f'SELECT id, data FROM "{entity}" WHERE id = $1',
                id
            )

            if not row:
                raise DocumentNotFound(entity, id)

            # Parse JSON string from JSONB column
            document = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
            document['id'] = row['id']

            # Delete document
            await conn.execute(
                f'DELETE FROM "{entity}" WHERE id = $1',
                id
            )

            return document, 1

    def _get_core_manager(self) -> CoreManager:
        """Get core manager instance"""
        return self.database.core

    def _prepare_datetime_fields(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for PostgreSQL storage (normalize to UTC with Z suffix)"""
        from datetime import datetime, timezone

        fields_meta = MetadataService.fields(entity)
        prepared_data = data.copy()

        for field, value in prepared_data.items():
            if value is None:
                continue

            field_meta = fields_meta.get(field, {})
            field_type = field_meta.get('type')

            if field_type == 'Datetime':
                if isinstance(value, datetime):
                    # Convert datetime object to UTC and format with Z suffix
                    dt_utc = value.astimezone(timezone.utc)
                    prepared_data[field] = dt_utc.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
                elif isinstance(value, str):
                    # Parse string (any timezone), convert to UTC, format with Z
                    try:
                        date_str = value.strip()
                        if date_str.endswith('Z'):
                            date_str = date_str[:-1] + '+00:00'
                        dt = datetime.fromisoformat(date_str)
                        # If naive datetime, assume UTC
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        dt_utc = dt.astimezone(timezone.utc)
                        prepared_data[field] = dt_utc.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
                    except (ValueError, TypeError):
                        pass
            elif field_type == 'Date':
                # Date fields: store as YYYY-MM-DD (no time component)
                if isinstance(value, datetime):
                    prepared_data[field] = value.strftime('%Y-%m-%d')
                elif isinstance(value, str):
                    try:
                        date_str = value.strip()
                        # Parse and reformat to ensure consistent YYYY-MM-DD format
                        if 'T' in date_str:
                            # Has time component - extract date only
                            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            prepared_data[field] = dt.strftime('%Y-%m-%d')
                        else:
                            # Already date-only, validate format
                            dt = datetime.strptime(date_str, '%Y-%m-%d')
                            prepared_data[field] = dt.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass

        return prepared_data

    def _convert_single_value(self, value: Any, field_type: str) -> Any:
        """Convert a single value to appropriate type for PostgreSQL"""
        if value is None:
            return value

        if field_type in ['Date', 'Datetime'] and isinstance(value, str):
            try:
                date_str = value.strip()
                if date_str.endswith('Z'):
                    date_str = date_str[:-1] + '+00:00'
                from datetime import datetime
                return datetime.fromisoformat(date_str).isoformat()
            except (ValueError, TypeError):
                return value

        return value

    async def _validate_unique_constraints(
        self,
        entity: str,
        data: Dict[str, Any],
        unique_constraints: List[List[str]],
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints for PostgreSQL"""
        return True  # PostgreSQL handles unique constraints natively via indexes
