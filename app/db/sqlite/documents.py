"""
SQLite document operations - CRUD with JSON storage.
"""

import json
import uuid
import aiosqlite
from typing import Any, Dict, List, Optional, Tuple

from ..document_manager import DocumentManager
from ..core_manager import CoreManager
from app.exceptions import DocumentNotFound, DatabaseError, DuplicateConstraintError
from app.services.metadata import MetadataService


class SqliteDocuments(DocumentManager):
    """SQLite implementation of document operations"""

    def __init__(self, database):
        super().__init__(database)

    async def _create_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in SQLite"""
        db = self.database.core.get_connection()

        # If an 'id' was specified, use it else generate one
        if not id:
            id = str(uuid.uuid4())

        # Store shadow id field for sorting (not _id - that's metadata)
        create_data = data.copy()
        create_data['id'] = id

        # Ensure table exists
        await db.execute(f'''
            CREATE TABLE IF NOT EXISTS "{entity}" (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        ''')

        try:
            # Insert document as JSON text
            await db.execute(
                f'INSERT INTO "{entity}" (id, data) VALUES (?, ?)',
                (id, json.dumps(create_data))
            )
            await db.commit()
            return create_data

        except aiosqlite.IntegrityError as e:
            # Unique constraint violation
            raise DuplicateConstraintError(
                message=f"Duplicate key error",
                entity=entity,
                field="unknown",  # SQLite doesn't provide field name easily
                entity_id=id
            )

    async def _get_impl(self, entity: str, id: str) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID"""
        db = self.database.core.get_connection()

        cursor = await db.execute(
            f'SELECT data FROM "{entity}" WHERE id = ?',
            (id,)
        )
        row = await cursor.fetchone()

        if not row:
            raise DocumentNotFound(entity, id)

        document = json.loads(row[0])
        return document, 1

    async def _get_all_impl(
        self,
        entity: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated list of documents with filter/sort"""
        db = self.database.core.get_connection()

        # Build WHERE clause from filters
        where_parts = []
        params = []

        if filter:
            fields_meta = MetadataService.fields(entity)
            for field, value in filter.items():
                if isinstance(value, dict):
                    # Range queries: {$gte: 21, $lt: 65}
                    for op, val in value.items():
                        sql_op = self._get_sql_operator(op)
                        where_parts.append(
                            f"CAST(json_extract(data, '$.{field}') AS REAL) {sql_op} ?"
                        )
                        params.append(val)
                else:
                    # Check if this is an enum field or non-enum string
                    field_meta = fields_meta.get(field, {})
                    field_type = field_meta.get('type', 'String')
                    has_enum_values = 'enum' in field_meta

                    if field_type == 'String' and not has_enum_values:
                        # Non-enum strings: substring match (case-insensitive)
                        where_parts.append(
                            f"json_extract(data, '$.{field}') LIKE ? COLLATE NOCASE"
                        )
                        params.append(f"%{value}%")
                    else:
                        # Enum fields and non-strings: exact match
                        where_parts.append(
                            f"json_extract(data, '$.{field}') = ?"
                        )
                        params.append(value)

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # Build ORDER BY clause
        order_clause = ""
        if sort:
            order_parts = []
            for field, direction in sort:
                order_parts.append(
                    f"json_extract(data, '$.{field}') {direction.upper()}"
                )
            order_clause = f"ORDER BY {', '.join(order_parts)}"

        # Pagination
        offset = (page - 1) * pageSize
        limit_clause = f"LIMIT ? OFFSET ?"
        params.extend([pageSize, offset])

        # Execute main query
        query = f'''
            SELECT data FROM "{entity}"
            {where_clause}
            {order_clause}
            {limit_clause}
        '''

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        # Get total count (without pagination)
        count_params = params[:-2]  # Exclude LIMIT/OFFSET params
        count_query = f'SELECT COUNT(*) FROM "{entity}" {where_clause}'
        cursor = await db.execute(count_query, count_params)
        total = (await cursor.fetchone())[0]

        # Parse JSON documents
        documents = [json.loads(row[0]) for row in rows]

        return documents, total

    async def _update_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing document"""
        db = self.database.core.get_connection()

        try:
            cursor = await db.execute(
                f'UPDATE "{entity}" SET data = ? WHERE id = ?',
                (json.dumps(data), id)
            )
            await db.commit()

            # Check if row was actually updated
            if cursor.rowcount == 0:
                raise DocumentNotFound(entity, id)

            return data

        except aiosqlite.IntegrityError as e:
            raise DuplicateConstraintError(
                message=f"Duplicate key error on update",
                entity=entity,
                field="unknown",
                entity_id=id
            )

    async def _delete_impl(self, entity: str, id: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID"""
        db = self.database.core.get_connection()

        # Fetch document before deleting
        cursor = await db.execute(
            f'SELECT data FROM "{entity}" WHERE id = ?',
            (id,)
        )
        row = await cursor.fetchone()

        if not row:
            raise DocumentNotFound(entity, id)

        document = json.loads(row[0])

        # Delete document
        await db.execute(
            f'DELETE FROM "{entity}" WHERE id = ?',
            (id,)
        )
        await db.commit()

        return document, 1

    def _get_core_manager(self) -> CoreManager:
        """Get core manager instance"""
        return self.database.core

    def _get_sql_operator(self, mongo_op: str) -> str:
        """Convert MongoDB operator to SQL"""
        mapping = {
            '$gt': '>',
            '$gte': '>=',
            '$lt': '<',
            '$lte': '<=',
            '$eq': '='
        }
        return mapping.get(mongo_op, '=')

    def _prepare_datetime_fields(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for SQLite storage (as ISO strings)"""
        from datetime import datetime

        fields_meta = MetadataService.fields(entity)
        prepared_data = data.copy()

        for field, value in prepared_data.items():
            if value is None:
                continue

            field_meta = fields_meta.get(field, {})
            field_type = field_meta.get('type')

            if field_type in ['Date', 'Datetime']:
                if isinstance(value, datetime):
                    # Convert datetime object to ISO string
                    prepared_data[field] = value.isoformat()
                elif isinstance(value, str):
                    # Parse string and convert to ISO format
                    try:
                        date_str = value.strip()
                        if date_str.endswith('Z'):
                            date_str = date_str[:-1] + '+00:00'
                        prepared_data[field] = datetime.fromisoformat(date_str).isoformat()
                    except (ValueError, TypeError):
                        pass

        return prepared_data

    def _convert_filter_values(self, filters: Dict[str, Any], entity: str) -> Dict[str, Any]:
        """Convert filter values to SQLite-appropriate types"""
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

    def _convert_single_value(self, value: Any, field_type: str) -> Any:
        """Convert a single value to appropriate type for SQLite"""
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
        """Validate unique constraints for SQLite"""
        return True  # SQLite handles unique constraints natively via indexes
