# Service Architecture Implementation - Current Work

**Date**: 2025-10-23
**Status**: In Progress - Implementing filter_matching parameter

---

## Background

Decided to implement **configuration-driven services** instead of code generation:
- Single provider implementation (e.g., `redis_provider.py`)
- Configuration in schema.yaml per entity
- Services read config from MetadataService at runtime
- See `docs/service_arch.md` for full architectural decision

---

## Current Implementation Task

**Goal**: Enable exact-match filtering in `get_all()` for authentication and other use cases.

**Problem**:
- Auth needs exact username match: `username="mark"` should only match `"mark"`, not `"Mark_Williams"`
- Current MongoDB implementation does substring matching for non-enum strings
- Led to authentication failures (wrong user matched)

**Solution**: Add `filter_matching` parameter to `get_all()` with modes:
- `"contains"` (default) - Current behavior, substring/fuzzy matching
- `"exact"` - Exact match only, needed for auth

---

## Work Completed

### 1. ✅ Services read metadata from MetadataService

**File**: `app/services/auth/cookies/redis_provider.py`

**Change**: Removed `field_map` parameter, now reads from entity metadata:

```python
async def login(self, entity_name: str, credentials: dict) -> str | None:
    # Get service configuration from entity metadata
    from app.services.metadata import MetadataService

    metadata = MetadataService.get(entity_name)
    services = metadata.get("services", {})
    auth_config = services.get("auth.cookies.redis", {})
    field_map = auth_config.get("fields", {})

    login_field = field_map.get("login")
    password_field = field_map.get("password")
    # ... rest of login logic
```

**Schema example** (already exists in `schema.yaml`):
```yaml
User:
  services:
    auth.cookies.redis:
      fields:
        login: username
        password: password
```

### 2. ✅ Added filter_matching parameter to DocumentManager

**File**: `app/db/document_manager.py`

**Changes**:

**`get_all()` signature** (line 27):
```python
async def get_all(
    self,
    entity: str,
    sort: Optional[List[Tuple[str, str]]] = None,
    filter: Optional[Dict[str, Any]] = None,
    page: int = 1,
    pageSize: int = 25,
    view_spec: Dict[str, Any] = {},
    filter_matching: str = "contains"  # NEW
) -> Tuple[List[Dict[str, Any]], int]:
```

**Abstract method** (line 73):
```python
@abstractmethod
async def _get_all_impl(
    self,
    entity: str,
    sort: Optional[List[Tuple[str, str]]] = None,
    filter: Optional[Dict[str, Any]] = None,
    page: int = 1,
    pageSize: int = 25,
    filter_matching: str = "contains"  # NEW
) -> Tuple[List[Dict[str, Any]], int]:
```

**Note**: Kept `get(id)` unchanged - it only does ID lookups, doesn't need filtering modes.

---

## Work In Progress

### 3. 🔨 Update MongoDB to respect filter_matching

**File**: `app/db/mongodb/documents.py`

**What needs to change**:

#### Part A: Update `_get_all_impl()` signature (line 26)

**Current**:
```python
async def _get_all_impl(
    self,
    entity: str,
    sort: Optional[List[Tuple[str, str]]] = None,
    filter: Optional[Dict[str, Any]] = None,
    page: int = 1,
    pageSize: int = 25
) -> Tuple[List[Dict[str, Any]], int]:
```

**Needs to be**:
```python
async def _get_all_impl(
    self,
    entity: str,
    sort: Optional[List[Tuple[str, str]]] = None,
    filter: Optional[Dict[str, Any]] = None,
    page: int = 1,
    pageSize: int = 25,
    filter_matching: str = "contains"  # NEW
) -> Tuple[List[Dict[str, Any]], int]:
```

#### Part B: Pass filter_matching to _build_query_filter (line 52)

**Current**:
```python
query = self._build_query_filter(case_filter, entity) if filter else {}
```

**Needs to be**:
```python
query = self._build_query_filter(case_filter, entity, filter_matching) if filter else {}
```

#### Part C: Update _build_query_filter() signature and logic (line 254)

**Current signature**:
```python
def _build_query_filter(self, filters: Dict[str, Any], entity: str) -> Dict[str, Any]:
```

**New signature**:
```python
def _build_query_filter(self, filters: Dict[str, Any], entity: str, filter_matching: str = "contains") -> Dict[str, Any]:
```

**Current logic** (lines 280-288):
```python
if field_type == 'String' and not has_enum_values:
    # Free text fields: partial match with regex
    query[field] = {"$regex": f".*{self._escape_regex(str(value))}.*", "$options": "i"}
else:
    # Enum fields and non-text fields: exact match
    if isinstance(value, str) and ObjectId.is_valid(value):
        query[field] = ObjectId(value)
    else:
        query[field] = value
```

**New logic needed**:
```python
if field_type == 'String' and not has_enum_values:
    if filter_matching == "exact":
        # Exact match for auth and other exact-match use cases
        query[field] = value
    else:
        # Free text fields: partial match with regex (default behavior)
        query[field] = {"$regex": f".*{self._escape_regex(str(value))}.*", "$options": "i"}
else:
    # Enum fields and non-text fields: always exact match
    if isinstance(value, str) and ObjectId.is_valid(value):
        query[field] = ObjectId(value)
    else:
        query[field] = value
```

**Key change**: When `filter_matching="exact"`, skip the regex wrapper for non-enum strings.

---

## Work Remaining

### 4. ⏳ Update Elasticsearch and SQLite

**Files**:
- `app/db/elasticsearch/documents.py`
- `app/db/sqlite/documents.py`

**Changes**: Add `filter_matching` parameter to `_get_all_impl()` (match MongoDB changes)

### 5. ⏳ Update redis_provider to use get_all with exact matching

**File**: `app/services/auth/cookies/redis_provider.py`

**Current code** (lines 120-135, has debug logging):
```python
# Query database for user
from app.db.factory import DatabaseFactory
db = DatabaseFactory.get_instance()

try:
    user_docs, count = await db.documents.get_all(
        entity_name,
        filter={login_field: login_value},
        pageSize=1
    )
    print(f"[DEBUG] Database query - count: {count}, filter: {{{login_field}: {login_value}}}")
except Exception as e:
    print(f"[DEBUG] Database error during login: {e}")
    return None

if count == 0:
    print(f"[DEBUG] No user found with {login_field}={login_value}")
    return None

user = user_docs[0]
print(f"[DEBUG] User found - checking password")
```

**Needs to be**:
```python
# Query database for user with EXACT match
from app.db.factory import DatabaseFactory
db = DatabaseFactory.get_instance()

try:
    user_docs, count = await db.documents.get_all(
        entity_name,
        filter={login_field: login_value},
        pageSize=1,
        filter_matching="exact"  # NEW - exact match for auth
    )
except Exception as e:
    # Log error but don't expose details
    print(f"Database error during login: {e}")
    return None

if count == 0:
    return None

user = user_docs[0]
```

### 6. ⏳ Remove debug logging from redis_provider.py

**File**: `app/services/auth/cookies/redis_provider.py`

Remove all `print(f"[DEBUG]...")` statements added during debugging.

### 7. ⏳ Update redis_user.py

**File**: `app/services/redis_user.py`

**Current** (lines 43-46):
```python
# Field mapping from schema
field_map = {"login": "username", "password": "password"}

# Authenticate and get session_id
session_id = await CookiesAuth().login("User", field_map, payload)
```

**Needs to be**:
```python
# Authenticate and get session_id (field_map now read from metadata)
session_id = await CookiesAuth().login("User", payload)
```

### 8. ⏳ Handle DocumentNotFound exception

**File**: `app/services/auth/cookies/redis_provider.py`

Add proper exception handling for case where user not found (currently returns empty list, not exception).

### 9. ⏳ Test with redis.sh

Run `./redis.sh` to verify:
- Login with correct credentials succeeds
- Session stored in Redis
- Logout clears session
- Exact matching works (no partial matches)

### 10. ⏳ Update generated model templates

**File**: `src/generators/templates/models/base.tpl`

**Current** (line ~35):
```python
@classmethod
async def get_all(cls,
                  sort: List[Tuple[str, str]],
                  filter: Optional[Dict[str, Any]],
                  page: int,
                  pageSize: int,
                  view_spec: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    db = DatabaseFactory.get_instance()
    return await db.documents.get_all("{{Entity}}", sort, filter, page, pageSize, view_spec)
```

**Needs**:
```python
@classmethod
async def get_all(cls,
                  sort: List[Tuple[str, str]],
                  filter: Optional[Dict[str, Any]],
                  page: int,
                  pageSize: int,
                  view_spec: Dict[str, Any],
                  filter_matching: str = "contains") -> Tuple[List[Dict[str, Any]], int]:
    db = DatabaseFactory.get_instance()
    return await db.documents.get_all("{{Entity}}", sort, filter, page, pageSize, view_spec, filter_matching)
```

### 11. ⏳ Regenerate models

Run model generator to update all entity models with new signature.

### 12. ⏳ Dynamic route registration

**Goal**: Replace `redis_user.py` file with dynamic route registration at startup.

**File**: `app/services/services_init.py`

**Concept**:
```python
async def initialize(app=None):
    # Load service registry
    ServiceRegistry.initialize()

    # Initialize Redis
    redis_config = Config.get("auth.cookies.redis", {})
    await CookiesAuth.initialize(redis_config)

    # Dynamic route registration for auth services
    if app:
        for entity_name in MetadataService.list_entities():
            metadata = MetadataService.get(entity_name)
            services = metadata.get("services", {})

            if "auth.cookies.redis" in services:
                register_auth_routes(app, entity_name, CookiesAuth)
```

**Implementation needed**: Create `register_auth_routes()` function that dynamically creates FastAPI routes.

### 13. ⏳ Prune services directory

Remove build-time files no longer needed:
- `app/services/auth/base_router.py` (was for code generation)
- `app/services/auth/base_model.py` (was for code generation)
- `app/services/framework/decorators.py` (was for code generation)
- Consider keeping `services_registry.json` for validation

---

## Files Modified So Far

1. ✅ `app/services/auth/cookies/redis_provider.py` - Reads field_map from metadata
2. ✅ `app/db/document_manager.py` - Added filter_matching parameter
3. ✅ `redis.sh` - Better error display, shows session ID on success

---

## Files Pending Changes

1. 🔨 `app/db/mongodb/documents.py` - Implement filter_matching logic
2. ⏳ `app/db/elasticsearch/documents.py` - Add filter_matching parameter
3. ⏳ `app/db/sqlite/documents.py` - Add filter_matching parameter
4. ⏳ `app/services/redis_user.py` - Remove hardcoded field_map
5. ⏳ `src/generators/templates/models/base.tpl` - Add filter_matching parameter
6. ⏳ `app/services/services_init.py` - Add dynamic route registration

---

## Testing Status

**Current issue**: Authentication failing because:
- MongoDB doing substring match on username
- "mark" matches "Mark_Williams_hotmail.com"
- Wrong user returned, password mismatch

**Fix**: Once filter_matching="exact" is implemented, auth will work correctly.

**Test command**: `./redis.sh`

---

## Next Steps (In Order)

1. Finish MongoDB filter_matching implementation (Part C above)
2. Update Elasticsearch and SQLite for consistency
3. Update redis_provider to use filter_matching="exact"
4. Remove debug logging
5. Update redis_user.py to use new signature
6. Test with redis.sh
7. Update model templates and regenerate
8. Implement dynamic route registration
9. Clean up services directory

---

## Related Documentation

- `docs/service_arch.md` - Architectural decision document
- `redis_todo.md` - Remaining Redis auth tasks (password hashing, etc.)
- `schema.yaml` - Service configurations per entity

---

## Decision Log

### Why filter_matching instead of match?
- `match` conflicts with Python's `re.match()`
- `filter_matching` is clearer about what it's matching
- Consistent with being a parameter about how filters work

### Why not use filter for get(id)?
- `get(id)` is a fast path for 90% of single-doc lookups
- ID lookups are always exact, no need for matching modes
- Keeps router code simple: `User.get(id)` vs `User.get_all(filter={"id": id})`

### Why add to get_all() instead of new method?
- Single method with modes is simpler than multiple methods
- Default "contains" preserves current behavior (no breaking changes)
- "exact" mode available when needed (auth, unique lookups)

---

## Code Snippets for Reference

### Schema Service Configuration
```yaml
User:
  services:
    auth.cookies.redis:
      fields:
        login: username
        password: password
```

### Auth Usage Pattern
```python
# In redis_provider.py
user_docs, count = await db.documents.get_all(
    entity_name,
    filter={login_field: login_value},
    pageSize=1,
    filter_matching="exact"
)
```

### Search Usage Pattern (current behavior)
```python
# In search endpoints
users, count = await db.documents.get_all(
    "User",
    filter={"username": "mar"},
    pageSize=10,
    filter_matching="contains"  # or omit, it's the default
)
```
