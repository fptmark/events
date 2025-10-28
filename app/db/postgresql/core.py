"""
PostgreSQL core manager - connection pool and initialization.
"""

import asyncpg
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urlunparse
from ..core_manager import CoreManager
from app.config import Config


class PostgreSQLCore(CoreManager):
    """PostgreSQL connection pool management"""

    def __init__(self, database):
        super().__init__(database)
        self.pool: Optional[asyncpg.Pool] = None
        self.db_uri = None

    async def init(self, db_uri: str, database_name: str = None):
        """Initialize PostgreSQL connection pool, creating database if needed"""
        self.db_uri = db_uri

        # Parse URI to extract database name
        parsed = urlparse(db_uri)
        target_db_name = parsed.path.lstrip('/') if parsed.path else database_name

        if not target_db_name:
            raise ValueError("Database name must be specified in URI or as parameter")

        # Create admin URI (connect to 'postgres' database)
        admin_parsed = parsed._replace(path='/postgres')
        admin_uri = urlunparse(admin_parsed)

        # Connect to postgres database to check/create target database
        try:
            conn = await asyncpg.connect(admin_uri)
            try:
                # Check if target database exists
                exists = await conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1",
                    target_db_name
                )

                # Create database if it doesn't exist
                if not exists:
                    logging.info(f"PostgreSQL: Creating database '{target_db_name}'")
                    # Cannot use parameterized query for CREATE DATABASE
                    await conn.execute(f'CREATE DATABASE "{target_db_name}"')
                    logging.info(f"PostgreSQL: Database '{target_db_name}' created")
                else:
                    logging.info(f"PostgreSQL: Database '{target_db_name}' already exists")
            finally:
                await conn.close()
        except Exception as e:
            logging.error(f"PostgreSQL: Failed to create database '{target_db_name}': {e}")
            raise

        # Now create connection pool to target database
        self.pool = await asyncpg.create_pool(
            db_uri,
            min_size=5,
            max_size=20,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            command_timeout=60
        )

        logging.info(f"PostgreSQL: Connected to {db_uri}, pool initialized")

    @property
    def id_field(self) -> str:
        """PostgreSQL uses 'id' as the ID field"""
        return "id"

    def get_id(self, document: Dict[str, Any]) -> Optional[str]:
        """Extract and normalize document ID"""
        return document.get('id')

    def get_connection(self):
        """Get connection pool (use pool.acquire() to get actual connection)"""
        return self.pool

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logging.info("PostgreSQL: Connection pool closed")

    def generate_id(self, entity: str) -> str:
        """Generate unique ID for entity using ULID"""
        from ulid import ULID
        return str(ULID()).lower()

    async def wipe_and_reinit(self) -> bool:
        """Wipe all data and reinitialize database"""
        if self.pool is None:
            return False

        try:
            async with self.pool.acquire() as conn:
                # Get all table names
                tables = await conn.fetch("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """)

                # Drop all tables
                for table_row in tables:
                    table_name = table_row['tablename']
                    await conn.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

            # Recreate tables and indexes from schema
            await self.database.documents.initialize_schema()

            logging.info("PostgreSQL: Database wiped and reinitialized")
            return True

        except Exception as e:
            logging.error(f"PostgreSQL wipe and reinit failed: {e}")
            return False

    async def get_status_report(self) -> dict:
        """Get comprehensive database status report"""
        if self.pool is None:
            return {
                "database": "postgresql",
                "status": "error",
                "entities": {},
                "error": "Not connected"
            }

        try:
            async with self.pool.acquire() as conn:
                # Get all tables
                tables = await conn.fetch("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """)

                entities = {}
                collections_details = {}

                for table_row in tables:
                    table_name = table_row['tablename']

                    # Get row count
                    count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')

                    # Get indexes
                    indexes = await conn.fetch("""
                        SELECT indexname FROM pg_indexes
                        WHERE schemaname = 'public' AND tablename = $1
                    """, table_name)

                    entities[table_name] = count
                    collections_details[table_name] = {
                        "doc_count": count,
                        "index_count": len(indexes),
                        "indexes": [idx['indexname'] for idx in indexes]
                    }

                return {
                    "database": "postgresql",
                    "status": "healthy",
                    "config": Config.get(""),
                    "entities": entities,
                    "details": {
                        "db_info": {
                            "uri": self.db_uri,
                            "type": "postgresql"
                        },
                        "collections": {
                            "total": len(tables),
                            "details": collections_details
                        }
                    }
                }

        except Exception as e:
            return {
                "database": "postgresql",
                "status": "error",
                "entities": {},
                "error": str(e)
            }
