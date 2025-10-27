"""
PostgreSQL index management - unique constraints.
"""

import asyncpg
from typing import List, Optional
import re

from ..index_manager import IndexManager
from app.exceptions import DatabaseError


class PostgreSQLIndexes(IndexManager):
    """PostgreSQL index operations"""

    def __init__(self, database):
        super().__init__(database)

    async def create(self, entity: str, fields: List[str], unique: bool = True, name: Optional[str] = None) -> None:
        """Create index on entity"""
        # For PostgreSQL with proper columns, indexes are created during table creation
        # Ensure table exists first by calling initialize_schema for this entity
        async with self.database.core.pool.acquire() as conn:
            # Check if table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = $1
                )
            """, entity)

            if not table_exists:
                # Table doesn't exist - call initialize_schema to create all tables
                await self.database.documents.initialize_schema()

        # Index already created with table, nothing more to do

    async def get_all(self, entity: str) -> List[List[str]]:
        """Get all unique indexes for entity as field lists"""
        async with self.database.core.pool.acquire() as conn:
            try:
                # Check if table exists
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = $1
                    )
                """, entity)

                if not table_exists:
                    return []  # Table doesn't exist yet

                field_lists = []

                # Get all indexes for this table
                indexes = await conn.fetch("""
                    SELECT
                        i.indexname,
                        i.indexdef
                    FROM pg_indexes i
                    WHERE i.schemaname = 'public'
                    AND i.tablename = $1
                    AND i.indexdef LIKE '%UNIQUE%'
                """, entity)

                for index_row in indexes:
                    index_def = index_row['indexdef']
                    # Parse field names from the index definition
                    fields = self._parse_fields_from_sql(index_def)

                    if fields:
                        field_lists.append(fields)

                return field_lists

            except asyncpg.PostgresError as e:
                raise DatabaseError(f"PostgreSQL get indexes error: {str(e)}")

    async def get_all_detailed(self, entity: str) -> dict:
        """Get all indexes with full details as dict[index_name, index_info]"""
        async with self.database.core.pool.acquire() as conn:
            try:
                # Check if table exists
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = $1
                    )
                """, entity)

                if not table_exists:
                    return {}

                indexes = {}

                # Get all indexes for this table
                index_list = await conn.fetch("""
                    SELECT
                        i.indexname,
                        i.indexdef
                    FROM pg_indexes i
                    WHERE i.schemaname = 'public'
                    AND i.tablename = $1
                """, entity)

                for index_row in index_list:
                    index_name = index_row['indexname']
                    index_def = index_row['indexdef']
                    is_unique = 'UNIQUE' in index_def.upper()

                    fields = self._parse_fields_from_sql(index_def)

                    indexes[index_name] = {
                        "fields": fields,
                        "unique": is_unique,
                        "type": "native"
                    }

                return indexes

            except asyncpg.PostgresError as e:
                raise DatabaseError(f"PostgreSQL get detailed indexes error: {str(e)}")

    async def delete(self, entity: str, fields: List[str]) -> None:
        """Delete index by field names"""
        async with self.database.core.pool.acquire() as conn:
            try:
                # Find the index name for these fields
                indexes = await conn.fetch("""
                    SELECT
                        i.indexname,
                        i.indexdef
                    FROM pg_indexes i
                    WHERE i.schemaname = 'public'
                    AND i.tablename = $1
                """, entity)

                for index_row in indexes:
                    index_name = index_row['indexname']
                    index_def = index_row['indexdef']
                    index_fields = self._parse_fields_from_sql(index_def)

                    if index_fields == fields:
                        # Found the matching index, drop it
                        await conn.execute(f"DROP INDEX IF EXISTS {index_name}")
                        return

            except asyncpg.PostgresError as e:
                raise DatabaseError(f"PostgreSQL delete index error: {str(e)}")

    def _parse_fields_from_sql(self, sql: str) -> List[str]:
        """Parse field names from CREATE INDEX SQL statement"""
        # Example: CREATE UNIQUE INDEX idx_User_email ON public."User" USING btree ((data ->> 'email'::text))
        # Example: CREATE UNIQUE INDEX idx_User_email_username ON public."User" USING btree ((data ->> 'email'::text), (data ->> 'username'::text))

        fields = []

        # Find all data->> patterns
        # Pattern matches: (data ->> 'fieldname'::text) or (data->>'fieldname')
        pattern = r"\(data\s*-?>?>?\s*'(\w+)'(?:::text)?\)"
        matches = re.findall(pattern, sql)

        return matches
