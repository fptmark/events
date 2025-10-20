# SQLite Driver Implementation Guide
**Project:** Events Framework REST API
**Goal:** Add SQLite database driver alongside MongoDB and Elasticsearch

---

## Architecture Overview

### Existing Structure
```
/app/db/
  base.py                    # DatabaseInterface (abstract base)
  core_manager.py            # CoreManager (abstract base)
  document_manager.py        # DocumentManager (abstract base)
  index_manager.py           # IndexManager (abstract base)
  factory.py                 # Database factory
  mongodb/                   # MongoDB implementation
    __init__.py
    core.py
    documents.py
    indexes.py
  elasticsearch/             # Elasticsearch implementation
    __init__.py
    core.py
    documents.py
    indexes.py
```

### New SQLite Structure
```
/app/db/sqlite/
  __init__.py               # SQLiteDatabase class
  core.py                   # SQLiteCore(CoreManager)
  documents.py              # SqliteDocuments(DocumentManager)
  indexes.py                # SqliteIndexes(IndexManager)
```

---

## Implementation Steps

### Step 1: Install Dependencies

```bash
pip install aiosqlite
```

**Note:** `sqlite3` is in Python stdlib, but `aiosqlite` provides async support.

---

### Step 2: Create `/app/db/sqlite/__init__.py`

```python
"""
SQLite database implementation.
Document-oriented storage using JSON columns.
"""

from ..base import DatabaseInterface
from .core import SQLiteCore
from .documents import SqliteDocuments
from .indexes import SqliteIndexes


class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation of DatabaseInterface"""

    def __init__(self, db_path: str = 'events.db', case_sensitive_sorting: bool = False):
        self.db_path = db_path
        super().__init__(case_sensitive_sorting)

    def _get_manager_classes(self) -> dict:
        """Return manager classes for SQLite"""
        return {
            'core': SQLiteCore,
            'documents': SqliteDocuments,
            'indexes': SqliteIndexes
        }

    async def supports_native_indexes(self) -> bool:
        """SQLite supports native unique indexes"""
        return True

    async def initialize(self):
        """Initialize SQLite database"""
        await self.core.initialize(self.db_path)
        self._initialized = True
        self._health_state = "healthy"
```

---

### Step 3: Create `/app/db/sqlite/core.py`

```python
"""
SQLite core manager - connection and initialization.
"""

import aiosqlite
from ..core_manager import CoreManager


class SQLiteCore(CoreManager):
    """SQLite connection management"""

    def __init__(self, database):
        super().__init__(database)
        self.connection = None

    async def initialize(self, db_path: str):
        """Initialize SQLite connection"""
        self.connection = await aiosqlite.connect(db_path)

        # Enable foreign key constraints
        await self.connection.execute("PRAGMA foreign_keys = ON")

        # Enable WAL mode for better concurrency
        await self.connection.execute("PRAGMA journal_mode = WAL")

        await self.connection.commit()

    def get_connection(self):
        """Get database connection"""
        return self.connection

    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()

    def generate_id(self, entity: str) -> str:
        """Generate unique ID for entity"""
        import uuid
        prefix = entity[:3].lower()
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
```

---

### Step 4: Create `/app/db/sqlite/documents.py`

```python
"""
SQLite document operations - CRUD with JSON storage.
"""

import json
import aiosqlite
from typing import Any, Dict, List, Optional, Tuple

from ..document_manager import DocumentManager
from ..core_manager import CoreManager
from app.exceptions import DocumentNotFound, DatabaseError, DuplicateConstraintError


class SqliteDocuments(DocumentManager):
    """SQLite implementation of document operations"""

    def __init__(self, database):
        super().__init__(database)

    async def _create_impl(self, entity: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document in SQLite"""
        db = self.database.core.get_connection()

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
                (id, json.dumps(data))
            )
            await db.commit()
            return data

        except aiosqlite.IntegrityError as e:
            # Unique constraint violation
            raise DuplicateConstraintError(
                message=f"Duplicate key error",
                entity=entity,
                field="unknown",  # SQLite doesn't provide field name easily
                entity_id=id
            )

    async def _get_impl(self, id: str, entity: str) -> Tuple[Dict[str, Any], int]:
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
                    # Equality filter
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
            await db.execute(
                f'UPDATE "{entity}" SET data = ? WHERE id = ?',
                (json.dumps(data), id)
            )
            await db.commit()

            # Check if row was actually updated
            if db.total_changes == 0:
                raise DocumentNotFound(entity, id)

            return data

        except aiosqlite.IntegrityError as e:
            raise DuplicateConstraintError(
                message=f"Duplicate key error on update",
                entity=entity,
                field="unknown",
                entity_id=id
            )

    async def _delete_impl(self, id: str, entity: str) -> Tuple[Dict[str, Any], int]:
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
```

---

### Step 5: Create `/app/db/sqlite/indexes.py`

```python
"""
SQLite index management - unique constraints.
"""

import aiosqlite
from typing import List

from ..index_manager import IndexManager


class SqliteIndexes(IndexManager):
    """SQLite index operations"""

    def __init__(self, database):
        super().__init__(database)

    async def create_unique_indexes(self, entity: str, unique_constraints: List[List[str]]):
        """Create unique indexes for constraints"""
        db = self.database.core.get_connection()

        for constraint_fields in unique_constraints:
            # Create unique index on field(s)
            if len(constraint_fields) == 1:
                # Single field unique constraint
                field = constraint_fields[0]
                index_name = f"idx_{entity}_{field}_unique"

                await db.execute(f'''
                    CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
                    ON "{entity}"(json_extract(data, '$.{field}'))
                ''')
            else:
                # Composite unique constraint
                field_extracts = [
                    f"json_extract(data, '$.{field}')"
                    for field in constraint_fields
                ]
                index_name = f"idx_{entity}_{'_'.join(constraint_fields)}_unique"

                await db.execute(f'''
                    CREATE UNIQUE INDEX IF NOT EXISTS {index_name}
                    ON "{entity}"({', '.join(field_extracts)})
                ''')

        await db.commit()

    async def create_performance_indexes(self, entity: str, fields: List[str]):
        """Create indexes for commonly filtered/sorted fields"""
        db = self.database.core.get_connection()

        for field in fields:
            index_name = f"idx_{entity}_{field}"

            await db.execute(f'''
                CREATE INDEX IF NOT EXISTS {index_name}
                ON "{entity}"(json_extract(data, '$.{field}'))
            ''')

        await db.commit()
```

---

### Step 6: Update `/app/db/factory.py`

Add SQLite to the database factory:

```python
def create_database(db_type: str, config: dict):
    """Factory to create database instances"""

    if db_type == 'mongodb':
        from .mongodb import MongoDatabase
        return MongoDatabase(
            connection_string=config.get('connection_string'),
            database_name=config.get('database_name')
        )

    elif db_type == 'elasticsearch':
        from .elasticsearch import ElasticsearchDatabase
        return ElasticsearchDatabase(
            hosts=config.get('hosts'),
            ...
        )

    elif db_type == 'sqlite':
        from .sqlite import SQLiteDatabase
        return SQLiteDatabase(
            db_path=config.get('path', 'events.db')
        )

    else:
        raise ValueError(f"Unknown database type: {db_type}")
```

---

### Step 7: Configuration

Add SQLite configuration option:

```python
# config.py or environment variables
DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'mongodb')  # mongodb, elasticsearch, sqlite
SQLITE_PATH = os.getenv('SQLITE_PATH', 'events.db')

# Usage
db = create_database(
    db_type=DATABASE_TYPE,
    config={
        'path': SQLITE_PATH  # for SQLite
    }
)
```

---

## Key Features Implemented

### 1. Document Storage as JSON
- Each entity gets a table with `id` and `data` columns
- Documents stored as JSON text in `data` column
- Same pattern as MongoDB/Elasticsearch (document-oriented)

### 2. Native Unique Constraints
- Uses SQLite's `CREATE UNIQUE INDEX` on JSON fields
- Immediate enforcement (ACID-compliant)
- No eventual consistency issues like Elasticsearch

### 3. Filter/Sort/Page Support
- **Filtering:** `WHERE json_extract(data, '$.field') = ?`
- **Sorting:** `ORDER BY json_extract(data, '$.field') ASC`
- **Pagination:** `LIMIT ? OFFSET ?`

### 4. Range Queries
- Supports MongoDB-style operators: `$gt`, `$gte`, `$lt`, `$lte`
- Casts JSON values to appropriate types for comparison

### 5. ACID Transactions
- All operations are transactional
- Automatic rollback on errors
- No race conditions on unique constraints

---

## Testing

### Basic Test Script

```python
import asyncio
from app.db.sqlite import SQLiteDatabase

async def test_sqlite():
    # Initialize
    db = SQLiteDatabase(db_path=':memory:')  # In-memory for testing
    await db.initialize()

    # Create document
    user_data = {
        'firstName': 'John',
        'lastName': 'Doe',
        'email': 'john@example.com',
        'gender': 'male',
        'netWorth': 50000
    }

    user_id = db.core.generate_id('User')
    result = await db.documents.create('User', user_id, user_data)
    print(f"Created: {result}")

    # Get document
    doc, count = await db.documents.get(user_id, 'User')
    print(f"Retrieved: {doc}")

    # Get all with filter
    docs, total = await db.documents.get_all(
        'User',
        filter={'gender': 'male'},
        sort=[('firstName', 'asc')],
        page=1,
        pageSize=25
    )
    print(f"Found {total} users: {docs}")

    # Clean up
    await db.core.close()

asyncio.run(test_sqlite())
```

### Run Existing Test Suite

```bash
# Set database type to SQLite
export DATABASE_TYPE=sqlite
export SQLITE_PATH=test_events.db

# Run tests
pytest tests/
```

---

## Performance Optimization

### Add Indexes for Common Queries

```python
# After initializing database
await db.indexes.create_performance_indexes('User', [
    'gender',      # Frequently filtered
    'firstName',   # Frequently sorted
    'lastName',    # Frequently sorted
    'email',       # Unique constraint
    'username'     # Unique constraint
])
```

### Enable WAL Mode (Already Done in Core)

```sql
PRAGMA journal_mode = WAL;
```
- Better concurrency (readers don't block writers)
- Faster commits
- Safer crash recovery

---

## Limitations

### 1. Single-Writer Concurrency
- Only one write transaction at a time
- Multiple concurrent readers OK
- Not suitable for high-concurrency production use

### 2. No Network Access
- File-based database
- Cannot connect from remote clients
- Suitable for: dev/test, embedded apps, demos

### 3. File Size Limits
- Practical limit around 1TB
- Rarely an issue for typical applications

---

## Use Cases

### ✅ Perfect For:
- Development environment (no Docker needed)
- CI/CD testing (fast, no external dependencies)
- Demos and prototypes
- Embedded applications
- Single-user applications

### ⚠️ Not Recommended For:
- High-concurrency production systems
- Multi-server deployments
- Applications requiring network database access

---

## Migration Path: SQLite → SQL Server

### Similarities (90% compatible)
```sql
-- Both use similar syntax:
CREATE TABLE [User] (id TEXT PRIMARY KEY, data TEXT);
SELECT json_extract(data, '$.field') FROM User;  -- SQLite
SELECT JSON_VALUE(data, '$.field') FROM [User];  -- SQL Server
```

### Key Changes for SQL Server
1. `json_extract()` → `JSON_VALUE()`
2. `?` placeholders → `@p1, @p2` placeholders
3. `LIMIT/OFFSET` → `OFFSET/FETCH NEXT`
4. Connection library: `aiosqlite` → `aioodbc`

### Estimated Migration Effort
- 80% of code reusable
- 2-3 days to port from SQLite to SQL Server

---

## Summary

**Implementation Time:** 1-2 days

**Complexity:** Low - straightforward async/await patterns

**Value:**
- Proves SQL works with document-oriented architecture
- Zero-deployment development mode
- Foundation for SQL Server implementation
- Permanent utility for testing

**Next Steps:**
1. Implement the 4 files above
2. Test with existing test suite
3. Add to factory and configuration
4. Document limitations clearly
5. Use as foundation for SQL Server later
