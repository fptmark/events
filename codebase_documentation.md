# Events Application Codebase Documentation

## Architecture Overview

### Database Layer (`app/db/`)
- **`base.py`**: Abstract `DatabaseInterface` with methods:
  - `get_all(collection, unique_constraints) -> Tuple[List[Dict], List[str], int]` (includes count)
  - `get_by_id(collection, doc_id, unique_constraints) -> Tuple[Dict, List[str]]`
  - `save_document(collection, data, unique_constraints) -> Tuple[Dict, List[str]]`
  - `delete_document(collection, doc_id) -> bool`

- **`mongodb.py`**: MongoDB implementation
  - Uses `count_documents({})` for total count in `get_all()`
  - Converts ObjectId to string for consistency
  - Returns lowercase hex ObjectId strings

- **`elasticsearch.py`**: Elasticsearch implementation  
  - Extracts count from `hits.total.value` in search response
  - Uses `size=1000` to handle pagination
  - Generates custom ObjectId strings for consistency with MongoDB

- **`factory.py`**: `DatabaseFactory` singleton
  - `get_all(collection, unique_constraints) -> Tuple[List[Dict], List[str], int]`
  - Normalizes database-specific types (ObjectId -> string)
  - Converts warnings to notifications

### Models Layer (`app/models/`)
All models follow consistent pattern:

- **`user_model.py`**: User class
  - `get_all() -> tuple[Sequence[Self], List[ValidationError], int]`
  - `get(id) -> tuple[Self, List[str]]`
  - `save() -> tuple[Self, List[str]]`

- **`account_model.py`**: Account class
  - Same methods as User model
  - Handles account-specific validation

### Router Layer (`app/routers/`)
- **`endpoint_handlers.py`**: Dynamic route handlers
  - `list_entities_handler(entity_cls, entity_name, request)` - **KEY FOR METADATA**
    - Calls `entity_cls.get_all()` to get data + count
    - Processes FK data with `add_view_data()`
    - Returns `notifications.to_response(entity_data, metadata={"total": count})`

- **`router_factory.py`**: Creates dynamic routes for entities
- **`router.py`**: Main router setup

### Notification System (`app/notification.py`)
- **`SimpleNotificationCollection`**: Collects warnings/errors/success messages
  - `to_response(data, metadata=None) -> Dict[str, Any]` - **UPDATED FOR METADATA**
  - Returns structure: `{"data": [...], "metadata": {...}, "message": str, "level": str}`

## Key Data Flow for List Endpoints

1. **Router** calls `entity_cls.get_all()`
2. **Model** calls `DatabaseFactory.get_all(collection)`
3. **DatabaseFactory** calls specific driver's `get_all()`
4. **Driver** returns `(List[Dict], List[warnings], int)`
5. **Model** validates data, returns `(List[Entity], List[ValidationError], int)`
6. **Router** processes FK data, calls `notifications.to_response(data, metadata)`
7. **Response**: `{"data": [...], "metadata": {"total": N}, "message": null, "level": null}`

## Recent Changes for Metadata Support

### Database Drivers
- Updated return signature: `get_all() -> Tuple[List[Dict], List[str], int]`
- MongoDB: Added `count_documents({})` call
- ES: Extract count from existing search response

### Models  
- Updated return signature: `get_all() -> tuple[Sequence[Self], List[ValidationError], int]`
- Pass through count without inspection (clean SoC)

### Router
- Extract count from model response
- Pass to `notifications.to_response(data, metadata={"total": count})`

### Notification System
- Added `metadata` parameter to `to_response()`
- Include metadata at top level of API response

## UI Integration Points

The UI needs to:
1. Parse the new response format with top-level `metadata`
2. Extract `metadata.total` for display in status bar
3. Handle `data` as direct array (not nested)

## File Locations
- **Models**: `app/models/*.py`
- **Database**: `app/db/*.py` 
- **Routers**: `app/routers/*.py`
- **Notifications**: `app/notification.py`
- **UI**: `ui/src/app/`