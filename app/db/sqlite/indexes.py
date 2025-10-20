"""
SQLite index management - unique constraints.
"""

import aiosqlite
from typing import List, Optional

from ..index_manager import IndexManager
from app.exceptions import DatabaseError


class SqliteIndexes(IndexManager):
    """SQLite index operations"""

    def __init__(self, database):
        super().__init__(database)

    async def create(self, entity: str, fields: List[str], unique: bool = True, name: Optional[str] = None) -> None:
        """Create index on entity"""
        db = self.database.core.get_connection()

        try:
            # Check if table exists first
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (entity,)
            )
            table_exists = await cursor.fetchone()

            if not table_exists:
                # Create table if it doesn't exist (similar to MongoDB pattern)
                await db.execute(f'''
                    CREATE TABLE IF NOT EXISTS "{entity}" (
                        id TEXT PRIMARY KEY,
                        data TEXT NOT NULL
                    )
                ''')
                await db.commit()

            # Generate index name if not provided
            if not name:
                field_str = '_'.join(fields)
                suffix = '_unique' if unique else ''
                name = f"idx_{entity}_{field_str}{suffix}"

            # Build field extracts for json_extract
            if len(fields) == 1:
                # Single field index
                field = fields[0]
                index_expr = f"json_extract(data, '$.{field}')"
            else:
                # Composite index
                field_extracts = [f"json_extract(data, '$.{field}')" for field in fields]
                index_expr = ', '.join(field_extracts)

            # Create index
            unique_clause = 'UNIQUE' if unique else ''
            await db.execute(f'''
                CREATE {unique_clause} INDEX IF NOT EXISTS {name}
                ON "{entity}"({index_expr})
            ''')
            await db.commit()

        except Exception as e:
            raise DatabaseError(f"SQLite create index error: {str(e)}")

    async def get_all(self, entity: str) -> List[List[str]]:
        """Get all unique indexes for entity as field lists"""
        db = self.database.core.get_connection()

        try:
            # Check if table exists
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (entity,)
            )
            if not await cursor.fetchone():
                return []  # Table doesn't exist yet

            field_lists = []

            # Get all indexes for this table
            cursor = await db.execute(
                f"PRAGMA index_list('{entity}')"
            )
            indexes = await cursor.fetchall()

            for index_row in indexes:
                # index_row: (seq, name, unique, origin, partial)
                is_unique = index_row[2] == 1

                if not is_unique:
                    continue  # Only return unique indexes

                index_name = index_row[1]

                # Get fields in this index
                cursor = await db.execute(f"PRAGMA index_info('{index_name}')")
                index_fields = await cursor.fetchall()

                # For SQLite with json_extract, we need to parse the field names
                # This is a simplified approach - assumes index was created by our create() method
                fields = []
                for field_info in index_fields:
                    # field_info: (seqno, cid, name)
                    # For json_extract indexes, name will be None and we need to look at the index SQL
                    pass

                # Alternative: get the SQL that created the index
                cursor = await db.execute(
                    "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                    (index_name,)
                )
                sql_row = await cursor.fetchone()
                if sql_row and sql_row[0]:
                    # Parse field names from the SQL
                    # Example: CREATE UNIQUE INDEX idx_User_email ON "User"(json_extract(data, '$.email'))
                    sql = sql_row[0]
                    fields = self._parse_fields_from_sql(sql)

                if fields:
                    field_lists.append(fields)

            return field_lists

        except Exception as e:
            raise DatabaseError(f"SQLite get indexes error: {str(e)}")

    async def get_all_detailed(self, entity: str) -> dict:
        """Get all indexes with full details as dict[index_name, index_info]"""
        db = self.database.core.get_connection()

        try:
            # Check if table exists
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (entity,)
            )
            if not await cursor.fetchone():
                return {}

            indexes = {}

            # Get all indexes for this table
            cursor = await db.execute(f"PRAGMA index_list('{entity}')")
            index_list = await cursor.fetchall()

            for index_row in index_list:
                index_name = index_row[1]
                is_unique = index_row[2] == 1

                # Get the SQL that created the index
                cursor = await db.execute(
                    "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                    (index_name,)
                )
                sql_row = await cursor.fetchone()
                fields = []
                if sql_row and sql_row[0]:
                    fields = self._parse_fields_from_sql(sql_row[0])

                indexes[index_name] = {
                    "fields": fields,
                    "unique": is_unique,
                    "type": "native"
                }

            return indexes

        except Exception as e:
            raise DatabaseError(f"SQLite get detailed indexes error: {str(e)}")

    async def delete(self, entity: str, fields: List[str]) -> None:
        """Delete index by field names"""
        db = self.database.core.get_connection()

        try:
            # Find the index name for these fields
            cursor = await db.execute(f"PRAGMA index_list('{entity}')")
            indexes = await cursor.fetchall()

            for index_row in indexes:
                index_name = index_row[1]

                # Get the SQL for this index
                cursor = await db.execute(
                    "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
                    (index_name,)
                )
                sql_row = await cursor.fetchone()
                if sql_row and sql_row[0]:
                    index_fields = self._parse_fields_from_sql(sql_row[0])
                    if index_fields == fields:
                        # Found the matching index, drop it
                        await db.execute(f"DROP INDEX IF EXISTS {index_name}")
                        await db.commit()
                        return

        except Exception as e:
            raise DatabaseError(f"SQLite delete index error: {str(e)}")

    def _parse_fields_from_sql(self, sql: str) -> List[str]:
        """Parse field names from CREATE INDEX SQL statement"""
        # Example: CREATE UNIQUE INDEX idx_User_email ON "User"(json_extract(data, '$.email'))
        # Example: CREATE UNIQUE INDEX idx_User_email_username ON "User"(json_extract(data, '$.email'), json_extract(data, '$.username'))

        import re
        fields = []

        # Find all json_extract patterns
        pattern = r"json_extract\(data,\s*'\$\.(\w+)'\)"
        matches = re.findall(pattern, sql)

        return matches
