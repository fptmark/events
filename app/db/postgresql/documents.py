"""
PostgreSQL document operations - CRUD with JSONB storage.
"""

import asyncpg
import json
from typing import Any, Dict, List, Optional, Tuple

from ..document_manager import DocumentManager
from ..core_manager import CoreManager
from app.core.exceptions import DocumentNotFound, DatabaseError, DuplicateConstraintError
from app.core.metadata import MetadataService


class PostgreSQLDocuments(DocumentManager):
    """PostgreSQL implementation of document operations using proper typed columns"""

    def __init__(self, database):
        super().__init__(database)

    def _get_postgres_type(self, field_meta: Dict[str, Any]) -> str:
        """Map schema field type to PostgreSQL column type"""
        field_type = field_meta.get('type', 'String')

        # Handle boolean types (Bool, Boolean) using first 4 chars for type safety
        if len(field_type) >= 4 and field_type[:4].lower() == 'bool':
            return 'BOOLEAN'

        type_map = {
            'String': 'TEXT',
            'Integer': 'INTEGER',
            'Number': 'NUMERIC',
            'Currency': 'NUMERIC(15,2)',
            'Float': 'DOUBLE PRECISION',
            'Date': 'DATE',
            'Datetime': 'TIMESTAMPTZ',
            'ObjectId': 'TEXT',
            'JSON': 'JSONB',
        }

        # Handle Array types: Array[String] -> TEXT[]
        if field_type.startswith('Array['):
            inner_type = field_type[6:-1]  # Extract 'String' from 'Array[String]'
            if inner_type == 'String':
                return 'TEXT[]'
            # Add other array types as needed
            return 'TEXT[]'

        return type_map.get(field_type, 'TEXT')

    def _build_create_table_sql(self, entity: str) -> Tuple[str, List[str], List[Tuple[str, ...]]]:
        """Build CREATE TABLE statement from entity metadata

        Returns:
            Tuple of (create_sql, unique_indexes, regular_indexes)
        """
        fields_meta = MetadataService.fields(entity)
        columns = ['id TEXT PRIMARY KEY']
        unique_indexes = []
        regular_indexes = []

        for field_name, field_meta in fields_meta.items():
            if field_name != 'id':
                col_type = self._get_postgres_type(field_meta)
                not_null = ' NOT NULL' if field_meta.get('required', False) else ''
                columns.append(f'"{field_name}" {col_type}{not_null}')

        # Get unique constraints from metadata
        entity_meta = MetadataService.get(entity)
        unique_constraints = entity_meta.get('uniques', []) if entity_meta else []

        for constraint_fields in unique_constraints:
            field_list = ', '.join([f'"{f}"' for f in constraint_fields])
            unique_indexes.append(f'CREATE UNIQUE INDEX IF NOT EXISTS "{entity.lower()}_{("_".join(constraint_fields))}_unique" ON "{entity}" ({field_list})')

        # Index all ObjectId fields (foreign keys)
        for field_name, field_meta in fields_meta.items():
            if field_meta.get('type') == 'ObjectId':
                regular_indexes.append((f'CREATE INDEX IF NOT EXISTS "{entity.lower()}_{field_name}_idx" ON "{entity}" ("{field_name}")',))

        create_sql = f'CREATE TABLE IF NOT EXISTS "{entity}" ({", ".join(columns)})'
        return create_sql, unique_indexes, regular_indexes

    def _convert_datetime(self, value: str) -> Any:
        """Convert ISO datetime string to timezone-aware datetime object"""
        from datetime import datetime, timezone
        if not isinstance(value, str):
            return value
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    def _convert_date(self, value: str) -> Any:
        """Convert ISO date string to date object (strips time if present)"""
        from datetime import datetime
        if not isinstance(value, str):
            return value
        return datetime.fromisoformat(value.replace('Z', '+00:00')).date()

    def _prepare_values_for_postgres(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python values to PostgreSQL-compatible format"""
        prepared = {}
        for field_name, value in data.items():
            if value is None:
                prepared[field_name] = None
            else:
                field_type = MetadataService.get(entity, field_name, 'type')
                # Handle boolean types (Bool, Boolean) using first 4 chars for type safety
                if field_type and len(field_type) >= 4 and field_type[:4].lower() == 'bool':
                    prepared[field_name] = bool(value)
                elif field_type == 'Date':
                    prepared[field_name] = self._convert_date(value)
                elif field_type == 'Datetime':
                    prepared[field_name] = self._convert_datetime(value)
                else:
                    prepared[field_name] = value
        return prepared

    async def _create_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in PostgreSQL with proper columns"""
        data.pop('id', None)

        async with self.database.core.pool.acquire() as conn:
            # Prepare values
            prepared_data = self._prepare_values_for_postgres(entity, data)
            prepared_data.pop('id', None)  # Ensure 'id' is not in prepared_data

            # Build INSERT statement dynamically
            fields = ['id'] + list(prepared_data.keys())
            placeholders = [f'${i+1}' for i in range(len(fields))]
            values = [id] + list(prepared_data.values())

            field_list = ', '.join([f'"{f}"' for f in fields])
            insert_sql = f'INSERT INTO "{entity}" ({field_list}) VALUES ({", ".join(placeholders)})'

            try:
                await conn.execute(insert_sql, *values)
                return {'id': id, **data}
            except asyncpg.UniqueViolationError as e:
                # Extract field name from constraint name (e.g., "user_username_unique" -> "username")
                field = None
                if hasattr(e, 'constraint_name') and e.constraint_name:
                    # Parse constraint name: entity_field1_field2_unique -> [field1, field2]
                    parts = e.constraint_name.split('_')
                    if parts[-1] == 'unique' and len(parts) > 2:
                        # Remove entity prefix and 'unique' suffix to get field name(s)
                        field_parts = parts[1:-1]
                        field = field_parts[0] if field_parts else None

                # Create user-friendly message
                field_display = field.capitalize() if field else "Field"
                message = f"{field_display} already exists"

                raise DuplicateConstraintError(
                    message=message,
                    entity=entity,
                    field=field,
                    entity_id=id
                )
            except asyncpg.NotNullViolationError as e:
                # Extract field name from column_name attribute
                field = e.column_name if hasattr(e, 'column_name') else None

                # Create user-friendly message
                field_display = field.capitalize() if field else "Field"
                message = f"{field_display} is required"

                from app.core.notify import Notification, HTTP
                Notification.error(HTTP.BAD_REQUEST, message, entity=entity, entity_id=id, field=field)
                raise  # Unreachable
            except asyncpg.PostgresError as e:
                raise DatabaseError(f"PostgreSQL error: {str(e)}")

    async def _get_impl(self, entity: str, id: str) -> Tuple[Dict[str, Any], int]:
        """Get single document by ID from proper columns"""
        async with self.database.core.pool.acquire() as conn:
            row = await conn.fetchrow(
                f'SELECT * FROM "{entity}" WHERE id = $1',
                id
            )

            if not row:
                raise DocumentNotFound(entity, id)

            # Convert row to dict
            document = dict(row)
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
        """Get paginated list of documents with filter/sort"""
        async with self.database.core.pool.acquire() as conn:
            # Build WHERE clause from filters
            where_parts = []
            params = []
            param_idx = 1

            if filter:
                for field, value in filter.items():
                    # Get properly cased field name
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
                            where_parts.append(f'"{proper_field}" {sql_op} ${param_idx}')
                            params.append(val)
                            param_idx += 1
                    else:
                        # Equality or substring match
                        field_meta = MetadataService.get(entity, proper_field) or {}
                        enum_values = field_meta.get('enum', None)
                        has_enum_values = enum_values is not None

                        if field_type == 'String' and not has_enum_values:
                            if substring_match:
                                where_parts.append(f'"{proper_field}" ILIKE ${param_idx}')
                                params.append(f"%{value}%")
                            else:
                                where_parts.append(f'"{proper_field}" ILIKE ${param_idx}')
                                params.append(value)
                        else:
                            # Exact match for enums, numbers, booleans, dates
                            # Convert date/datetime values for filters
                            if field_type == 'Date':
                                value = self._convert_date(value)
                            elif field_type == 'Datetime':
                                value = self._convert_datetime(value)
                            where_parts.append(f'"{proper_field}" = ${param_idx}')
                            params.append(value)

                        param_idx += 1

            where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

            # Build ORDER BY clause
            order_clause = ""
            if sort:
                order_parts = []
                for field, direction in sort:
                    # Convert field name to proper case (e.g., 'firstname' -> 'firstName')
                    proper_field = MetadataService.get_proper_name(entity, field)
                    field_type = MetadataService.get(entity, proper_field, 'type') or 'String'

                    # Only apply LOWER() to String fields (not numeric, date, etc.)
                    if self.database.case_sensitive_sorting:
                        sort_expr = f'"{proper_field}" {direction.upper()}'
                    else:
                        if field_type == 'String':
                            sort_expr = f'LOWER("{proper_field}") {direction.upper()}'
                        else:
                            sort_expr = f'"{proper_field}" {direction.upper()}'

                    # Always put NULLs last for better UX - users want to see actual data first
                    sort_expr += ' NULLS LAST'
                    order_parts.append(sort_expr)
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
                SELECT * FROM "{entity}"
                {where_clause}
                {order_clause}
                {limit_clause}
            '''

            rows = await conn.fetch(query, *params)

            # Get total count (without pagination)
            count_params = params[:-2]  # Exclude LIMIT/OFFSET params
            count_query = f'SELECT COUNT(*) FROM "{entity}" {where_clause}'
            total = await conn.fetchval(count_query, *count_params) if count_params else await conn.fetchval(count_query)

            # Convert rows to dicts
            documents = [dict(row) for row in rows]

            return documents, total

    async def _update_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update document with proper columns"""
        data.pop('id', None)

        async with self.database.core.pool.acquire() as conn:
            # Prepare values
            prepared_data = self._prepare_values_for_postgres(entity, data)
            prepared_data.pop('id', None)  # Ensure 'id' is not in prepared_data

            # Build UPDATE statement dynamically
            set_parts = []
            values = []
            param_idx = 1
            for field_name, value in prepared_data.items():
                set_parts.append(f'"{field_name}" = ${param_idx}')
                values.append(value)
                param_idx += 1

            values.append(id)  # Add id for WHERE clause
            update_sql = f'UPDATE "{entity}" SET {", ".join(set_parts)} WHERE id = ${param_idx}'

            try:
                result = await conn.execute(update_sql, *values)

                # asyncpg returns "UPDATE N" where N is row count
                if result == "UPDATE 0":
                    raise DocumentNotFound(entity, id)

                # Return with 'id' for API response
                return {'id': id, **data}

            except asyncpg.UniqueViolationError as e:
                # Extract field name from constraint name (e.g., "user_username_unique" -> "username")
                field = None
                if hasattr(e, 'constraint_name') and e.constraint_name:
                    # Parse constraint name: entity_field1_field2_unique -> [field1, field2]
                    parts = e.constraint_name.split('_')
                    if parts[-1] == 'unique' and len(parts) > 2:
                        # Remove entity prefix and 'unique' suffix to get field name(s)
                        field_parts = parts[1:-1]
                        field = field_parts[0] if field_parts else None

                # Create user-friendly message
                field_display = field.capitalize() if field else "Field"
                message = f"{field_display} already exists"

                raise DuplicateConstraintError(
                    message=message,
                    entity=entity,
                    field=field,
                    entity_id=id
                )
            except asyncpg.NotNullViolationError as e:
                # Extract field name from column_name attribute
                field = e.column_name if hasattr(e, 'column_name') else None

                # Create user-friendly message
                field_display = field.capitalize() if field else "Field"
                message = f"{field_display} is required"

                from app.core.notify import Notification, HTTP
                Notification.error(HTTP.BAD_REQUEST, message, entity=entity, entity_id=id, field=field)
                raise  # Unreachable
            except asyncpg.PostgresError as e:
                raise DatabaseError(f"PostgreSQL error: {str(e)}")

    async def _delete_impl(self, entity: str, id: str) -> Tuple[Dict[str, Any], int]:
        """Delete document by ID from proper columns"""
        async with self.database.core.pool.acquire() as conn:
            # Fetch document before deleting
            row = await conn.fetchrow(
                f'SELECT * FROM "{entity}" WHERE id = $1',
                id
            )

            if not row:
                raise DocumentNotFound(entity, id)

            # Convert row to dict
            document = dict(row)

            # Delete document
            await conn.execute(
                f'DELETE FROM "{entity}" WHERE id = $1',
                id
            )

            return document, 1

    async def initialize_schema(self) -> None:
        """Create all tables and indexes for all entities (called during wipe_and_reinit)"""
        from app.core.metadata import MetadataService

        async with self.database.core.pool.acquire() as conn:
            for entity in MetadataService.list_entities():
                # Build and execute CREATE TABLE
                create_sql, unique_indexes, regular_indexes = self._build_create_table_sql(entity)
                await conn.execute(create_sql)

                # Create unique indexes
                for idx_sql in unique_indexes:
                    await conn.execute(idx_sql)

                # Create regular indexes
                for idx_sql in regular_indexes:
                    await conn.execute(idx_sql[0])

    def _get_core_manager(self) -> CoreManager:
        """Get core manager instance"""
        return self.database.core

    def _prepare_datetime_fields(self, entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare datetime fields - delegates to _prepare_values_for_postgres"""
        return self._prepare_values_for_postgres(entity, data)

    async def _validate_unique_constraints(
        self,
        entity: str,
        data: Dict[str, Any],
        unique_constraints: List[List[str]],
        exclude_id: Optional[str] = None
    ) -> bool:
        """Validate unique constraints for PostgreSQL"""
        return True  # PostgreSQL handles unique constraints natively via indexes
