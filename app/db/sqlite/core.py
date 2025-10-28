"""
SQLite core manager - connection and initialization.
"""

import aiosqlite
import logging
from typing import Dict, Any, Optional
from ..core_manager import CoreManager


class SQLiteCore(CoreManager):
    """SQLite connection management"""

    def __init__(self, database):
        super().__init__(database)
        self.connection = None
        self.db_path = None

    async def init(self, db_path: str, database_name: str = None):
        """Initialize SQLite connection"""
        self.db_path = db_path
        self.connection = await aiosqlite.connect(db_path)

        # Enable foreign key constraints
        await self.connection.execute("PRAGMA foreign_keys = ON")

        # Enable WAL mode for better concurrency
        await self.connection.execute("PRAGMA journal_mode = WAL")

        await self.connection.commit()
        logging.info(f"SQLite: Connected to {db_path}")

    @property
    def id_field(self) -> str:
        """SQLite uses 'id' as the ID field"""
        return "id"

    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize document ID"""
        return document.get('id')

    def get_connection(self):
        """Get database connection"""
        return self.connection

    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logging.info("SQLite: Connection closed")

    def generate_id(self, entity: str) -> str:
        """Generate unique ID for entity"""
        import uuid
        prefix = entity[:3].lower()
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    async def wipe_and_reinit(self) -> bool:
        """Wipe all data and reinitialize database with proper schema"""
        if self.connection is None:
            return False

        try:
            # Get all table names
            cursor = await self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = await cursor.fetchall()

            # Drop all tables
            for table in tables:
                await self.connection.execute(f'DROP TABLE IF EXISTS "{table[0]}"')

            await self.connection.commit()

            # Recreate all tables with proper schemas from metadata
            from app.services.metadata import MetadataService
            for entity in MetadataService.list_entities():
                create_sql = self.database.documents._build_create_table_sql(entity)
                await self.connection.execute(create_sql)

            await self.connection.commit()

            logging.info("SQLite: Database wiped and reinitialized with proper schemas")
            return True

        except Exception as e:
            logging.error(f"SQLite wipe and reinit failed: {e}")
            return False

    async def get_status_report(self) -> dict:
        """Get comprehensive database status report"""
        if self.connection is None:
            return {
                "database": "sqlite",
                "status": "error",
                "entities": {},
                "error": "Not connected"
            }

        try:
            # Get all tables
            cursor = await self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            tables = await cursor.fetchall()

            entities = {}
            collections_details = {}

            for table in tables:
                table_name = table[0]

                # Get row count
                cursor = await self.connection.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                count = (await cursor.fetchone())[0]

                # Get indexes
                cursor = await self.connection.execute(
                    f"SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",(table_name,)
                )
                indexes = await cursor.fetchall()

                entities[table_name] = count
                collections_details[table_name] = {
                    "doc_count": count,
                    "index_count": len(indexes),
                    "indexes": [idx[0] for idx in indexes]
                }

            return {
                "database": "sqlite",
                "status": "healthy",
                "entities": entities,
                "details": {
                    "db_info": {
                        "path": self.db_path,
                        "type": "sqlite"
                    },
                    "collections": {
                        "total": len(tables),
                        "details": collections_details
                    }
                }
            }

        except Exception as e:
            return {
                "database": "sqlite",
                "status": "error",
                "entities": {},
                "error": str(e)
            }
