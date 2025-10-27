# PostgreSQL Driver Implementation Plan

## Overview

Create PostgreSQL database driver following the exact same pattern as existing drivers (MongoDB, Elasticsearch, SQLite). Use JSONB storage strategy with `id` + `data` column structure (same as SQLite).

**Estimated effort:** 4-6 hours
**Code reuse:** ~90% from SQLite driver
**Abstraction changes:** None needed

## File Structure

```
app/db/postgresql/
├── __init__.py          # PostgreSQLDatabase class
├── core.py              # PostgreSQLCore (connection pool)
├── documents.py         # PostgreSQLDocuments (CRUD)
└── indexes.py           # PostgreSQLIndexes (optional, future)

postgresql.json          # Config file (root)
```

## Dependencies

Add to `requirements.txt`:
```
asyncpg>=0.29.0
```

Install:
```bash
pip install asyncpg
```

## Implementation Steps

### Step 1: Create PostgreSQLCore (app/db/postgresql/core.py)

**Base:** Copy from `app/db/sqlite/core.py`

**Key changes:**
```python
import asyncpg
from typing import Optional
from ..core_manager import CoreManager

class PostgreSQLCore(CoreManager):
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.id_field = "id"
        self.case_sensitive_sorting = True
        self.supports_transactions = True

    async def initialize(self, uri: str, db_name: str):
        """Create connection pool"""
        # URI: postgresql://user:password@localhost:5432/dbname
        self.pool = await asyncpg.create_pool(
            uri,
            min_size=5,
            max_size=20,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            command_timeout=60
        )

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()

    def get_connection(self):
        """Return pool for acquiring connections"""
        return self.pool

    async def generate_id(self) -> str:
        """Generate ULID for new documents"""
        from ulid import ULID
        return str(ULID())
```

**Differences from SQLite:**
- Connection pool instead of single connection
- Pool lifecycle management
- Connection timeout settings

### Step 2: Create PostgreSQLDocuments (app/db/postgresql/documents.py)

**Base:** Copy from `app/db/sqlite/documents.py`

**Key changes:**

#### 2a. Connection Pattern

**SQLite:**
```python
db = self.database.core.get_connection()
cursor = await db.execute(query, params)
row = await cursor.fetchone()
```

**PostgreSQL:**
```python
async with self.database.core.pool.acquire() as conn:
    row = await conn.fetchrow(query, *params)
    rows = await conn.fetch(query, *params)
    value = await conn.fetchval(query, *params)
```

#### 2b. Parameter Placeholders

**SQLite:** `?`
**PostgreSQL:** `$1, $2, $3, ...`

Replace:
```python
# SQLite
query = "SELECT * FROM User WHERE id = ?"
params = (id,)

# PostgreSQL
query = "SELECT * FROM User WHERE id = $1"
params = (id,)
```

**Helper:** Track parameter index:
```python
param_idx = 1
where_parts.append(f"data->>'{field}' = ${param_idx}")
params.append(value)
param_idx += 1
```

#### 2c. JSON Operators

**SQLite:** `json_extract(data, '$.field')`
**PostgreSQL:** `data->>'field'` (returns text) or `data->'field'` (returns JSONB)

Replace all:
```python
# SQLite
f"json_extract(data, '$.{field}') = ?"

# PostgreSQL
f"data->>'{field}' = ${param_idx}"  # Text comparison
f"(data->>'{field}')::NUMERIC"       # Cast to number for range queries
```

#### 2d. ILIKE for Case-Insensitive

**SQLite:** `LIKE ? COLLATE NOCASE`
**PostgreSQL:** `ILIKE` (case-insensitive LIKE)

```python
# SQLite
f"json_extract(data, '$.{field}') LIKE ? COLLATE NOCASE"
params.append(f"%{value}%")

# PostgreSQL
f"data->>'{field}' ILIKE ${param_idx}"
params.append(f"%{value}%")
```

#### 2e. Type Casting

PostgreSQL requires explicit casts for numeric comparisons:

```python
# For range queries ($gte, $lte, etc.)
f"(data->>'{field}')::NUMERIC {sql_op} ${param_idx}"
```

#### 2f. Exception Handling

```python
import asyncpg

try:
    await conn.execute(insert_query, id, data)
except asyncpg.UniqueViolationError:
    raise DuplicateConstraintError(...)
except asyncpg.PostgresError as e:
    raise DatabaseError(...)
```

### Step 3: Create PostgreSQLDatabase (app/db/postgresql/__init__.py)

**Base:** Copy from `app/db/sqlite/__init__.py`

```python
"""PostgreSQL database implementation using JSONB storage"""

from ..base import DatabaseInterface
from .core import PostgreSQLCore
from .documents import PostgreSQLDocuments
# from .indexes import PostgreSQLIndexes  # Future

class PostgreSQLDatabase(DatabaseInterface):
    """PostgreSQL implementation with JSONB column storage"""

    def __init__(self):
        self.core = PostgreSQLCore()
        self.documents = PostgreSQLDocuments(self)
        # self.indexes = PostgreSQLIndexes(self)  # Future
        self.case_sensitive_sorting = True

    async def initialize(self, uri: str, db_name: str):
        """Initialize PostgreSQL connection pool"""
        await self.core.initialize(uri, db_name)

    async def close(self):
        """Close PostgreSQL connection pool"""
        await self.core.close()
```

### Step 4: Register in DatabaseFactory (app/db/factory.py)

Add PostgreSQL to factory:

```python
# In DatabaseFactory.initialize()

if db_type == "postgresql":
    from .postgresql import PostgreSQLDatabase
    cls._instance = PostgreSQLDatabase()
    await cls._instance.initialize(db_uri, db_name)
    logger.info("PostgreSQL database initialized successfully")
```

### Step 5: Create Configuration File (postgresql.json)

```json
{
  "database": {
    "type": "postgresql",
    "uri": "postgresql://localhost:5432/events",
    "name": "events"
  }
}
```

**With authentication:**
```json
{
  "database": {
    "type": "postgresql",
    "uri": "postgresql://user:password@localhost:5432/events",
    "name": "events"
  }
}
```

## Testing

### Setup PostgreSQL

```bash
# Install PostgreSQL (macOS)
brew install postgresql@16
brew services start postgresql@16

# Create database
createdb events

# Or with psql
psql postgres
CREATE DATABASE events;
\q
```

### Run Tests

```bash
# Run REST API
python main.py postgresql.json

# Run validator
cd test/validate-src
./validate --reset

# Run MCP validator
cd test/mcp-validate
python validate_mcp.py --config ../../postgresql.json --verbose
```

## Code Reference: Key Differences

### _create_impl

```python
# SQLite
await db.execute(
    f'INSERT INTO "{entity}" (id, data) VALUES (?, ?)',
    (id, json.dumps(data))
)

# PostgreSQL
await conn.execute(
    f'INSERT INTO "{entity}" (id, data) VALUES ($1, $2)',
    id, data  # asyncpg handles dict->JSONB conversion automatically
)
```

### _get_impl

```python
# SQLite
cursor = await db.execute(
    f'SELECT id, data FROM "{entity}" WHERE id = ?',
    (id,)
)
row = await cursor.fetchone()
if not row:
    raise DocumentNotFound(entity, id)
document = json.loads(row[1])
document['id'] = row[0]

# PostgreSQL
row = await conn.fetchrow(
    f'SELECT id, data FROM "{entity}" WHERE id = $1',
    id
)
if not row:
    raise DocumentNotFound(entity, id)
document = dict(row['data'])  # asyncpg returns dict from JSONB
document['id'] = row['id']
```

### _get_all_impl - WHERE Clause

```python
# SQLite
where_parts.append(
    f"json_extract(data, '$.{field}') LIKE ? COLLATE NOCASE"
)
params.append(f"%{value}%")

# PostgreSQL
where_parts.append(f"data->>'{field}' ILIKE ${param_idx}")
params.append(f"%{value}%")
param_idx += 1
```

### _get_all_impl - ORDER BY

```python
# SQLite
collate = "" if case_sensitive else " COLLATE NOCASE"
order_parts.append(
    f"json_extract(data, '$.{field}'){collate} {direction.upper()}"
)

# PostgreSQL
# Case-insensitive by default with ILIKE, or use LOWER()
if case_sensitive:
    order_parts.append(f"data->>'{field}' {direction.upper()}")
else:
    order_parts.append(f"LOWER(data->>'{field}') {direction.upper()}")
```

### _get_all_impl - Main Query

```python
# SQLite
cursor = await db.execute(query, params)
rows = await cursor.fetchall()

# Count
cursor = await db.execute(count_query, count_params)
total = (await cursor.fetchone())[0]

# Parse
for row in rows:
    doc = json.loads(row[1])
    doc['id'] = row[0]
    documents.append(doc)

# PostgreSQL
rows = await conn.fetch(query, *params)
total = await conn.fetchval(count_query, *count_params)

# Parse
for row in rows:
    doc = dict(row['data'])
    doc['id'] = row['id']
    documents.append(doc)
```

### _update_impl

```python
# SQLite
cursor = await db.execute(
    f'UPDATE "{entity}" SET data = ? WHERE id = ?',
    (json.dumps(data), id)
)
await db.commit()
if cursor.rowcount == 0:
    raise DocumentNotFound(entity, id)

# PostgreSQL
result = await conn.execute(
    f'UPDATE "{entity}" SET data = $1 WHERE id = $2',
    data, id
)
# asyncpg returns "UPDATE 1" or "UPDATE 0"
if result == "UPDATE 0":
    raise DocumentNotFound(entity, id)
```

### _delete_impl

```python
# SQLite
cursor = await db.execute(
    f'DELETE FROM "{entity}" WHERE id = ?',
    (id,)
)
await db.commit()
return cursor.rowcount > 0

# PostgreSQL
result = await conn.execute(
    f'DELETE FROM "{entity}" WHERE id = $1',
    id
)
return result == "DELETE 1"
```

## Post-Implementation

### Create Indexes

After driver works, create GIN indexes for performance:

```python
# In PostgreSQLIndexes or manual SQL
async def create_default_indexes(self, entity: str):
    """Create recommended indexes for entity"""
    async with self.database.core.pool.acquire() as conn:
        # GIN index on entire JSONB
        await conn.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_{entity.lower()}_data
            ON "{entity}" USING GIN (data)
        ''')

        # Field-specific indexes (optional)
        # await conn.execute(f'''
        #     CREATE INDEX IF NOT EXISTS idx_{entity.lower()}_email
        #     ON "{entity}" ((data->>'email'))
        # ''')
```

### Monitor Performance

```sql
-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Check slow queries
SELECT * FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

## Troubleshooting

### Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Check connection
psql -h localhost -p 5432 -U postgres -d events
```

### Permission Issues

```sql
-- Create user with permissions
CREATE USER events_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE events TO events_user;
```

### Pool Exhaustion

Increase pool size in `core.py`:
```python
self.pool = await asyncpg.create_pool(
    uri,
    min_size=10,    # Increase
    max_size=50,    # Increase
)
```

## Validation Checklist

After implementation:

- [ ] Install asyncpg dependency
- [ ] Create all three files (__init__.py, core.py, documents.py)
- [ ] Register in DatabaseFactory
- [ ] Create postgresql.json config
- [ ] Start PostgreSQL server
- [ ] Create database
- [ ] Run main.py with postgresql.json
- [ ] Test GET /api/db/report (should show "postgresql")
- [ ] Create test user via POST
- [ ] Get test user via GET
- [ ] List users via GET /api/User
- [ ] Update user via PUT
- [ ] Delete user via DELETE
- [ ] Run full validator test suite
- [ ] Check for connection leaks (pool status)
- [ ] Create GIN indexes for performance
- [ ] Compare performance with MongoDB/SQLite

## Migration Notes

### From SQLite to PostgreSQL

```bash
# 1. Export SQLite data
python main.py sqlite.json
curl http://localhost:5500/api/User > users.json

# 2. Switch to PostgreSQL
python main.py postgresql.json

# 3. Import data
cat users.json | jq '.data[]' | while read user; do
  curl -X POST http://localhost:5500/api/User \
    -H "Content-Type: application/json" \
    -d "$user"
done
```

### From MongoDB to PostgreSQL

Same process - JSON data is compatible.

## Future Enhancements

### Transactions Support

```python
async def create_user_with_account(user_data, account_data):
    async with self.database.core.pool.acquire() as conn:
        async with conn.transaction():
            account = await create_account(account_data)
            user_data['accountId'] = account['id']
            user = await create_user(user_data)
            return user, account
```

### Full-Text Search

```sql
-- Add tsvector column
ALTER TABLE "User"
ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', data->>'firstName' || ' ' || data->>'lastName')
) STORED;

CREATE INDEX idx_user_search ON "User" USING GIN (search_vector);

-- Search query
SELECT * FROM "User"
WHERE search_vector @@ to_tsquery('John & Doe');
```

### Replication

Configure streaming replication for HA (out of scope for driver).

## Summary

**Implementation order:**
1. Install asyncpg
2. Create core.py (connection pool)
3. Create documents.py (copy SQLite, update syntax)
4. Create __init__.py (database interface)
5. Register in factory.py
6. Create postgresql.json
7. Test with existing test suite

**Key syntax changes:**
- `?` → `$1, $2, $3`
- `json_extract(data, '$.field')` → `data->>'field'`
- `LIKE ? COLLATE NOCASE` → `ILIKE $n`
- Single connection → Connection pool
- `json.loads()` → asyncpg handles automatically

**Effort:** 4-6 hours (mostly find/replace from SQLite)

**Result:** Production-ready PostgreSQL driver with JSONB storage, connection pooling, and excellent performance.
