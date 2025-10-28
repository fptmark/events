"""
SQLite document operations - CRUD with JSON storage.
"""

import json
import uuid
import sqlite3
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

    def _get_sqlite_type(self, field_type: str) -> str:
        """Map schema field type to SQLite type"""
        type_map = {
            'String': 'TEXT',
            'Integer': 'INTEGER',
            'Boolean': 'INTEGER',  # SQLite uses 0/1 for boolean
            'Number': 'REAL',
            'Currency': 'REAL',
            'Float': 'REAL',
            'Date': 'TEXT',  # Store as ISO date string YYYY-MM-DD
            'Datetime': 'TEXT',  # Store as ISO datetime string
            'ObjectId': 'TEXT',
            'JSON': 'TEXT',  # Store as JSON string
        }
        return type_map.get(field_type, 'TEXT')

    def _build_create_table_sql(self, entity: str) -> str:
        """Build CREATE TABLE statement from entity metadata"""
        fields_meta = MetadataService.fields(entity)
        columns = ['id TEXT PRIMARY KEY']

        # Get uniques list from metadata
        uniques_list = MetadataService.get(entity).get('uniques') or []

        for field_name, field_meta in fields_meta.items():
            if field_name != 'id':
                field_type = field_meta.get('type', 'String')
                sql_type = self._get_sqlite_type(field_type)
                required = field_meta.get('required', False) or field_meta.get('autoGenerate', False) or field_meta.get('autoUpdate', False)

                column_def = f'{field_name} {sql_type}'
                if required:
                    column_def += ' NOT NULL'
                if [field_name] in uniques_list:
                    column_def += ' UNIQUE'
                columns.append(column_def)
            
        for constraint_fields in uniques_list:
            if len(constraint_fields) > 1:
                fields_str = ', '.join(f'"{f}"' for f in constraint_fields)
                columns.append(f'UNIQUE({fields_str})')

        return f'CREATE TABLE IF NOT EXISTS "{entity}" ({", ".join(columns)})'

    def _convert_datetime(self, value: str) -> str:
        """Convert datetime value to ISO string for SQLite storage"""
        from datetime import datetime, timezone
        if not isinstance(value, str):
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            return str(value)
        # Normalize to ISO format
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        dt_utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return dt_utc.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

    def _convert_date(self, value: str) -> str:
        """Convert date value to YYYY-MM-DD string for SQLite storage"""
        from datetime import datetime
        if not isinstance(value, str):
            if hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d')
            return str(value)
        # Parse and extract date only
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')

    def _prepare_values_for_sqlite(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python values to SQLite-compatible format"""
        prepared = {}
        for field_name, value in data.items():
            if value is None:
                prepared[field_name] = None
            else:
                field_type = MetadataService.get(entity, field_name, 'type')
                if field_type == 'Date':
                    prepared[field_name] = self._convert_date(value)
                elif field_type == 'Datetime':
                    prepared[field_name] = self._convert_datetime(value)
                elif field_type == 'Boolean':
                    prepared[field_name] = 1 if value else 0
                elif field_type == 'JSON':
                    prepared[field_name] = json.dumps(value) if not isinstance(value, str) else value
                else:
                    prepared[field_name] = value
        return prepared

    async def initialize_schema(self):
        """Create all tables with proper schemas from metadata"""
        db = self.database.core.get_connection()
        for entity in MetadataService.list_entities():
            create_sql = self._build_create_table_sql(entity)
            await db.execute(create_sql)
        await db.commit()

    async def _create_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in SQLite with proper columns"""
        db = self.database.core.get_connection()
        data.pop('id', None)

        # Prepare values
        prepared_data = self._prepare_values_for_sqlite(entity, data)

        # Build INSERT statement dynamically
        fields = ['id'] + list(prepared_data.keys())
        placeholders = ', '.join(['?' for _ in fields])
        fields_str = ', '.join(f'"{f}"' for f in fields)
        values = [id] + list(prepared_data.values())

        try:
            await db.execute(
                f'INSERT INTO "{entity}" ({fields_str}) VALUES ({placeholders})',
                values
            )
            await db.commit()
            return {'id': id, **data}

        except (aiosqlite.IntegrityError, sqlite3.IntegrityError) as e:
            raise DuplicateConstraintError(
                message=f"Duplicate key error",
                entity=entity,
                field="unknown",
                entity_id=id
            )

    async def _get_impl(self, entity: str, id: str) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID from proper columns"""
        db = self.database.core.get_connection()

        cursor = await db.execute(
            f'SELECT * FROM "{entity}" WHERE id = ?',
            (id,)
        )
        row = await cursor.fetchone()

        if not row:
            raise DocumentNotFound(entity, id)

        # Convert row to dict using column names
        document = dict(zip([d[0] for d in cursor.description], row))

        # Convert boolean values back from 0/1
        fields_meta = MetadataService.fields(entity)
        for field_name, value in document.items():
            if value is not None:
                field_type = MetadataService.get(entity, field_name, 'type')
                if field_type == 'Boolean':
                    document[field_name] = bool(value)
                elif field_type == 'JSON' and isinstance(value, str):
                    document[field_name] = json.loads(value)

        return document, 1

    async def _get_all_impl(
        self,
        entity: str,
        sort: Optional[List[Tuple[str, str]]] = None,
        filter: Optional[Dict[str, Any]] = None,
        page: int = 1,
        pageSize: int = 25,
        substring_match: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get paginated list of documents with filter/sort on proper columns"""
        db = self.database.core.get_connection()

        # Build WHERE clause from filters
        where_parts = []
        params = []

        if filter:
            for field, value in filter.items():
                proper_field = MetadataService.get_proper_name(entity, field)
                field_type = MetadataService.get(entity, proper_field, 'type') or 'String'

                if isinstance(value, dict):
                    # Range queries: {$gte: 21, $lt: 65} or date ranges
                    for op, val in value.items():
                        sql_op = self._map_operator(op)
                        # Convert date/datetime values for filters
                        if field_type == 'Date':
                            val = self._convert_date(val)
                        elif field_type == 'Datetime':
                            val = self._convert_datetime(val)
                        where_parts.append(f'"{proper_field}" {sql_op} ?')
                        params.append(val)
                else:
                    # Equality or substring match
                    field_meta = MetadataService.get(entity, proper_field) or {}
                    enum_values = field_meta.get('enum', None)
                    has_enum_values = enum_values is not None

                    if field_type == 'String' and not has_enum_values:
                        if substring_match:
                            where_parts.append(f'"{proper_field}" LIKE ? COLLATE NOCASE')
                            params.append(f"%{value}%")
                        else:
                            where_parts.append(f'"{proper_field}" = ? COLLATE NOCASE')
                            params.append(value)
                    else:
                        # Exact match for enums, numbers, booleans, dates
                        # Convert date/datetime values for filters
                        if field_type == 'Date':
                            value = self._convert_date(value)
                        elif field_type == 'Datetime':
                            value = self._convert_datetime(value)
                        elif field_type == 'Boolean':
                            value = 1 if value else 0
                        where_parts.append(f'"{proper_field}" = ?')
                        params.append(value)

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # Build ORDER BY clause
        order_clause = ""
        if sort:
            order_parts = []
            for field, direction in sort:
                proper_field = MetadataService.get_proper_name(entity, field)
                field_type = MetadataService.get(entity, proper_field, 'type') or 'String'

                # Only apply COLLATE NOCASE to String fields (not numeric, date, etc.)
                if self.database.case_sensitive_sorting:
                    sort_expr = f'"{proper_field}" {direction.upper()}'
                else:
                    if field_type == 'String':
                        sort_expr = f'"{proper_field}" COLLATE NOCASE {direction.upper()}'
                    else:
                        sort_expr = f'"{proper_field}" {direction.upper()}'

                order_parts.append(sort_expr)
            order_clause = f"ORDER BY {', '.join(order_parts)}"
        else:
            # Default sort by 'id' column for consistent pagination
            collate = "" if self.database.case_sensitive_sorting else " COLLATE NOCASE"
            order_clause = f"ORDER BY id{collate} ASC"

        # Pagination
        offset = self._calculate_pagination_offset(page, pageSize)
        limit_clause = f"LIMIT ? OFFSET ?"
        params.extend([pageSize, offset])

        # Execute main query
        query = f'SELECT * FROM "{entity}" {where_clause} {order_clause} {limit_clause}'
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

        # Save column names before executing COUNT query
        column_names = [d[0] for d in cursor.description]

        # Get total count (without pagination)
        count_params = params[:-2]  # Exclude LIMIT/OFFSET params
        count_query = f'SELECT COUNT(*) FROM "{entity}" {where_clause}'
        count_cursor = await db.execute(count_query, count_params)
        total = (await count_cursor.fetchone())[0]

        # Convert rows to documents
        documents = []
        for row in rows:
            document = dict(zip(column_names, row))

            # Convert boolean values back from 0/1
            for field_name, value in document.items():
                if value is not None:
                    field_type = MetadataService.get(entity, field_name, 'type')
                    if field_type == 'Boolean':
                        document[field_name] = bool(value)
                    elif field_type == 'JSON' and isinstance(value, str):
                        document[field_name] = json.loads(value)

            documents.append(document)

        return documents, total

    async def _update_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update document with proper columns"""
        db = self.database.core.get_connection()
        data.pop('id', None)

        # Prepare values
        prepared_data = self._prepare_values_for_sqlite(entity, data)

        # Build UPDATE statement dynamically
        set_parts = []
        values = []
        for field_name, value in prepared_data.items():
            set_parts.append(f'"{field_name}" = ?')
            values.append(value)

        values.append(id)  # Add id for WHERE clause

        try:
            cursor = await db.execute(
                f'UPDATE "{entity}" SET {", ".join(set_parts)} WHERE id = ?',
                values
            )
            await db.commit()

            if cursor.rowcount == 0:
                raise DocumentNotFound(entity, id)

            return {'id': id, **data}

        except (aiosqlite.IntegrityError, sqlite3.IntegrityError) as e:
            raise DuplicateConstraintError(
                message=f"Duplicate key error on update",
                entity=entity,
                field="unknown",
                entity_id=id
            )
        except Exception as e:
            print(f"Database error during update: {str(e)}")
            raise DatabaseError(f"Database error during update: {str(e)}")

    async def _delete_impl(self, entity: str, id: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID from proper columns"""
        db = self.database.core.get_connection()

        # Fetch document before deleting
        cursor = await db.execute(
            f'SELECT * FROM "{entity}" WHERE id = ?',
            (id,)
        )
        row = await cursor.fetchone()

        if not row:
            raise DocumentNotFound(entity, id)

        # Convert row to dict using column names
        document = dict(zip([d[0] for d in cursor.description], row))

        # Convert boolean values back from 0/1
        for field_name, value in document.items():
            if value is not None:
                field_type = MetadataService.get(entity, field_name, 'type')
                if field_type == 'Boolean':
                    document[field_name] = bool(value)
                elif field_type == 'JSON' and isinstance(value, str):
                    document[field_name] = json.loads(value)

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

    def _prepare_datetime_fields(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime fields for SQLite storage (normalize to UTC with Z suffix)"""
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
