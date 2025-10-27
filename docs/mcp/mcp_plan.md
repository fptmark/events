# MCP Implementation Plan

## Project Overview

**Objective**: Add MCP (Model Context Protocol) server as a parallel interface to the Events API, enabling AI assistants to query and manipulate data using natural language.

**Approach**: Build MCP layer on top of existing DocumentManager, reusing all business logic, validation, and database access code. Include RBAC-based security with dedicated MCP service user.

**Timeline**: 6 days (3 phases)

**Risk**: Low - No changes to existing codebase

**Security**: Role-based access control (RBAC) with dedicated `ai_agent` role for MCP operations

---

## Architecture

### Current Architecture
```
┌─────────────────┐
│   REST API      │
│  (FastAPI)      │
└────────┬────────┘
         │
         ├─→ endpoint_handlers.py
         │
         ↓
   ┌─────────────────┐
   │ DocumentManager │
   │  - MongoDB      │
   │  - Elasticsearch│
   │  - SQLite       │
   └─────────┬───────┘
             │
             ↓
        ┌────────┐
        │   DB   │
        └────────┘
```

### Target Architecture
```
┌─────────────────┐      ┌─────────────────┐
│   REST API      │      │   MCP Server    │ ← NEW
│  (FastAPI)      │      │ (stdio/SSE)     │
│                 │      │ Auth: ai_agent  │ ← RBAC
└────────┬────────┘      └────────┬────────┘
         │                        │
         ├─→ endpoint_handlers    │
         │   (user auth ctx)      ├─→ mcp_tools.py ← NEW
         │                        │   (claude_mcp ctx)
         │                        │
         └────────────┬───────────┘
                      ↓
            ┌─────────────────┐
            │ DocumentManager │ ← NO CHANGES
            │  + RBAC checks  │ ← Auth context aware
            │  - MongoDB      │
            │  - Elasticsearch│
            │  - SQLite       │
            └─────────┬───────┘
                      │
                      ↓
                 ┌────────┐
                 │   DB   │
                 └────────┘
```

**Key Principles**:
- MCP is a thin wrapper that calls the same DocumentManager methods as REST
- MCP server auto-authenticates as service user `claude_mcp` with `ai_agent` role
- All tool calls execute with MCP user's auth context and RBAC permissions
- Field-level and query-level restrictions enforced via RBAC

---

## File Structure

### New Files to Create

```
app/
  mcp/
    __init__.py                 # Package init
    server.py                   # MCP server setup and lifecycle
    tools.py                    # Tool implementations (CRUD + auth)
    schemas.py                  # Auto-generate tool schemas from metadata
    registry.py                 # Register all tools with MCP server
    auth.py                     # MCP auth context and service user
    rbac.py                     # RBAC permissions and enforcement
    utils.py                    # Helper functions

docs/
  mcp/
    setup.md                    # How to run MCP server
    tools.md                    # Tool reference documentation
    examples.md                 # Example queries

tests/
  mcp/
    test_tools.py              # Tool unit tests
    test_schemas.py            # Schema generation tests
    test_auth.py               # Auth tests
```

### Files to Modify

```
requirements.txt               # Add: mcp
app/models/user_model.py       # Add ai_agent role to RoleEnum
app/models/user_model.py       # Add RBAC metadata to User._metadata
config/
  mongo.json                   # Add MCP config section (auth credentials)
  es.json                      # Add MCP config section (auth credentials)
  sqlite.json                  # Add MCP config section (auth credentials)
```

**NO modifications to:**
- `app/db/` - All database code (reused as-is)
- `app/services/` - All service code (reused as-is)
- `app/routers/` - All REST code (unchanged)
- Business logic, validation, FK checks (all reused)

---

## MCP Authentication & RBAC Strategy

### Overview

MCP server operates with a dedicated service user (`claude_mcp`) that has the `ai_agent` role. This provides:
- **Security**: Least-privilege access for AI operations
- **Auditability**: All MCP actions tied to service user
- **Control**: RBAC defines what AI can and cannot do
- **Flexibility**: Easy to adjust permissions without code changes

### Authentication Layers

#### Layer 1: Process-Level Security
```json
// Claude Desktop config (~/.config/Claude/claude_desktop_config.json)
{
  "mcpServers": {
    "events-api": {
      "command": "python",
      "args": ["/path/to/events/mcp_server.py"],
      "env": {
        "MCP_USER": "claude_mcp",
        "MCP_PASSWORD": "secure_token_from_keychain"
      }
    }
  }
}
```

- MCP server is local process (trusted execution environment)
- Credentials in environment variables (not hardcoded)
- Auto-authenticates on startup

#### Layer 2: Tool-Level RBAC
```python
async def list_users(**kwargs):
    # Every tool call uses MCP service user context
    auth_context = server.get_mcp_auth_context()  # claude_mcp / ai_agent

    # RBAC checks before execution
    if not rbac.has_permission(auth_context, "User", "read"):
        raise PermissionError("ai_agent role cannot read User")

    # Execute with restrictions
    return await db.get_all("User", auth_context=auth_context, **kwargs)
```

### RBAC Model

#### Service User
```python
# Created during setup (one-time)
{
  "id": "usr_mcp_claude",
  "username": "claude_mcp",
  "email": "mcp@system.internal",
  "role": "ai_agent",
  "isAccountOwner": False,
  "accountId": "acc_system"
}
```

#### Role Definition
```python
# Added to User._metadata
_metadata = {
    # ... existing metadata ...
    "rbac": {
        "admin": {
            "read": True, "create": True, "update": True, "delete": True
        },
        "read": {
            "read": True, "create": False, "update": False, "delete": False
        },
        "ai_agent": {  # ← New role for MCP
            "read": True,          # Can list/get entities
            "create": True,        # Can create entities
            "update": False,       # Cannot modify existing
            "delete": False,       # Cannot delete

            # Field-level restrictions
            "field_restrictions": {
                "password": "write_only",  # Can set, never read
                "role": "read_only",       # Can view, cannot change
            },

            # Query restrictions
            "max_page_size": 100,  # Prevent huge queries
            "allowed_filters": ["username", "email", "gender", "createdAt"],
            "forbidden_filters": ["password"]  # Cannot filter by password
        }
    }
}
```

#### Per-Entity Permissions
```python
# RBAC rules per entity
rbac_config = {
    "User": {
        "ai_agent": {
            "read": True,
            "create": True,    # Can help create users
            "update": False,   # Cannot modify users
            "delete": False
        }
    },
    "Account": {
        "ai_agent": {
            "read": True,      # Can view accounts
            "create": False,   # Cannot create accounts
            "update": False,
            "delete": False
        }
    },
    "Profile": {
        "ai_agent": {
            "read": True,
            "create": True,
            "update": True,    # Can help users update profiles
            "delete": False
        }
    }
}
```

### Security Features

#### 1. Field Masking
```python
async def list_users(**kwargs):
    result = await db.get_all("User", **kwargs)

    # Mask sensitive fields for MCP
    for user in result["data"]:
        if "password" in user:
            del user["password"]  # Never return passwords

    return result
```

#### 2. Audit Logging
```python
import logging
audit_logger = logging.getLogger("mcp.audit")

async def list_users(**kwargs):
    audit_logger.info({
        "action": "list_users",
        "user": "claude_mcp",
        "role": "ai_agent",
        "filters": kwargs.get("filter"),
        "timestamp": datetime.now()
    })

    return await db.get_all("User", **kwargs)
```

#### 3. Rate Limiting
```python
from functools import wraps
import time

def rate_limit(max_calls=100, per_seconds=60):
    """Prevent MCP abuse"""
    calls = []

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            now = time.time()
            calls[:] = [c for c in calls if c > now - per_seconds]

            if len(calls) >= max_calls:
                raise Exception(f"Rate limit exceeded: {max_calls}/{per_seconds}s")

            calls.append(now)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=100, per_seconds=60)
async def list_users(**kwargs):
    ...
```

#### 4. Query Restrictions
```python
async def list_users(pageSize=25, **kwargs):
    # Enforce max page size for ai_agent
    max_allowed = rbac.get_max_page_size("User", "ai_agent")  # 100

    if pageSize > max_allowed:
        pageSize = max_allowed

    return await db.get_all("User", page_size=pageSize, **kwargs)
```

### Auth Flow

```
┌────────────────┐
│ MCP Server     │
│ Startup        │
└───────┬────────┘
        │
        ├─1. Read MCP_USER, MCP_PASSWORD from environment
        │
        ↓
┌────────────────┐
│ Authenticate   │
│ as claude_mcp  │
└───────┬────────┘
        │
        ├─2. Verify credentials in User table
        ├─3. Load user: usr_mcp_claude (role: ai_agent)
        │
        ↓
┌────────────────┐
│ Create Auth    │
│ Context        │
└───────┬────────┘
        │
        ├─4. Store in server: auth_context = {user, role}
        │
        ↓
┌────────────────┐
│ Tool Call      │
│ list_users()   │
└───────┬────────┘
        │
        ├─5. Get auth_context from server
        ├─6. Check RBAC: ai_agent.User.read = True ✅
        ├─7. Check filters allowed ✅
        ├─8. Enforce max_page_size = 100
        ├─9. Execute query with auth_context
        ├─10. Mask password fields
        ├─11. Log to audit trail
        │
        ↓
┌────────────────┐
│ Return Results │
└────────────────┘
```

### Setup Checklist

- [ ] Add `ai_agent` to RoleEnum in user_model.py
- [ ] Add RBAC metadata to User._metadata
- [ ] Create MCP service user (usr_mcp_claude)
- [ ] Set MCP_PASSWORD in environment/keychain
- [ ] Implement rbac.py with permission checks
- [ ] Add field masking in tool handlers
- [ ] Add audit logging
- [ ] Test RBAC denies unauthorized actions
- [ ] Document ai_agent role permissions

---

## Phase 1: Proof of Concept (2 days)

### Goal
Validate that MCP works with our architecture by implementing basic server and 3 tools.

### Day 1: Setup & Basic Server

#### Task 1.1: Install Dependencies
```bash
# Add to requirements.txt
mcp==0.9.0

# Install
pip install mcp
```

#### Task 1.2: Create MCP Server (`app/mcp/server.py`)
```python
"""
MCP server for Events API.
Exposes database entities and operations as MCP tools.
"""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from app.config import Config
from app.db import DatabaseFactory
from app.services.metadata import MetadataService
from app.services.model import ModelService

# Import tools
from .tools import get_all_tools
from .auth import initialize_auth

class EventsMCPServer:
    """MCP server wrapping Events API"""

    def __init__(self):
        self.server = Server("events-api")
        self.db = None
        self._initialized = False

    async def initialize(self):
        """Initialize database and services"""
        if self._initialized:
            return

        # Load config (same as REST)
        config_path = "mongo.json"  # TODO: Make configurable
        Config.initialize(config_path)

        # Initialize database (same as REST)
        db_config = Config.get("database")
        db_type = db_config.get("type", "mongodb")
        db_uri = db_config.get("uri")
        db_name = db_config.get("name")

        self.db = await DatabaseFactory.initialize(db_type, db_uri, db_name)

        # Initialize metadata service (same as REST)
        entities = [
            "Account", "User", "Profile", "TagAffinity",
            "Event", "UserEvent", "Url", "Crawl"
        ]
        MetadataService.initialize(entities)
        ModelService.initialize(entities)

        # Initialize auth
        await initialize_auth()

        self._initialized = True

    async def shutdown(self):
        """Cleanup on server shutdown"""
        if self.db:
            await DatabaseFactory.close()

    def register_tools(self):
        """Register all MCP tools"""
        tools = get_all_tools()

        for tool in tools:
            self.server.add_tool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["input_schema"],
                handler=tool["handler"]
            )

    async def run(self):
        """Run the MCP server"""
        await self.initialize()
        self.register_tools()

        # Run stdio server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Entry point for MCP server"""
    server = EventsMCPServer()
    try:
        await server.run()
    finally:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

#### Task 1.3: Add MCP Entry Point
Create `mcp_server.py` in project root:
```python
#!/usr/bin/env python3
"""
MCP server entry point.
Usage: python mcp_server.py
"""
from app.mcp.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
```

Make it executable:
```bash
chmod +x mcp_server.py
```

**Deliverable**: MCP server that starts and initializes database.

---

### Day 2: Implement 3 Basic Tools

#### Task 2.1: Create Tool Infrastructure (`app/mcp/tools.py`)
```python
"""
MCP tool implementations.
Each tool is a thin wrapper around DocumentManager.
"""
from typing import Dict, List, Any, Optional
from app.db import DatabaseFactory
from app.services.metadata import MetadataService


class ToolRegistry:
    """Registry of all MCP tools"""

    def __init__(self):
        self.tools = []

    def register(self, name: str, description: str, input_schema: Dict, handler):
        """Register a tool"""
        self.tools.append({
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": handler
        })

    def get_all(self) -> List[Dict]:
        """Get all registered tools"""
        return self.tools


# Global registry
registry = ToolRegistry()


def tool(name: str, description: str, input_schema: Dict):
    """Decorator to register a tool"""
    def decorator(func):
        registry.register(name, description, input_schema, func)
        return func
    return decorator


# =============================================================================
# User Tools (Phase 1: Basic Implementation)
# =============================================================================

@tool(
    name="list_users",
    description="List users with optional filtering, sorting, and pagination",
    input_schema={
        "type": "object",
        "properties": {
            "filter": {
                "type": "object",
                "description": "Filter users by field values (supports MongoDB operators)",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string"},
                    "gender": {"type": "string", "enum": ["male", "female", "other"]},
                    "role": {"type": "string", "enum": ["admin", "read"]},
                    "isAccountOwner": {"type": "boolean"},
                    "accountId": {"type": "string"}
                }
            },
            "filter_matching": {
                "type": "string",
                "enum": ["exact", "contains", "fuzzy"],
                "default": "exact",
                "description": "String matching strategy (MongoDB only)"
            },
            "sort": {
                "type": "array",
                "description": "Sort specification",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string",
                            "enum": ["username", "email", "firstName", "lastName", "createdAt", "updatedAt"]
                        },
                        "direction": {"type": "string", "enum": ["asc", "desc"]}
                    },
                    "required": ["field", "direction"]
                }
            },
            "page": {"type": "integer", "minimum": 1, "default": 1},
            "pageSize": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25}
        }
    }
)
async def list_users(
    filter: Optional[Dict] = None,
    filter_matching: str = "exact",
    sort: Optional[List[Dict]] = None,
    page: int = 1,
    pageSize: int = 25
) -> Dict[str, Any]:
    """List users - calls same DocumentManager method as REST"""

    db = DatabaseFactory.get_instance()

    result = await db.get_all(
        entity_name="User",
        filters=filter,
        filter_matching=filter_matching,
        sort_by=sort,
        page=page,
        page_size=pageSize
    )

    return {
        "users": result["data"],
        "pagination": result.get("pagination", {}),
        "total": result.get("pagination", {}).get("totalRecords", 0)
    }


@tool(
    name="get_user",
    description="Get a single user by ID",
    input_schema={
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "User ID"
            }
        },
        "required": ["id"]
    }
)
async def get_user(id: str) -> Dict[str, Any]:
    """Get user by ID - calls same DocumentManager method as REST"""

    db = DatabaseFactory.get_instance()

    result = await db.get_by_id("User", id)

    if not result:
        raise ValueError(f"User {id} not found")

    return {"user": result}


@tool(
    name="create_user",
    description="Create a new user",
    input_schema={
        "type": "object",
        "properties": {
            "username": {"type": "string", "minLength": 3, "maxLength": 50},
            "email": {"type": "string", "minLength": 8, "maxLength": 50},
            "password": {"type": "string", "minLength": 8},
            "firstName": {"type": "string", "minLength": 3, "maxLength": 100},
            "lastName": {"type": "string", "minLength": 3, "maxLength": 100},
            "isAccountOwner": {"type": "boolean"},
            "accountId": {"type": "string"},
            "gender": {"type": "string", "enum": ["male", "female", "other"]},
            "role": {"type": "string", "enum": ["admin", "read"]},
            "dob": {"type": "string", "format": "date"},
            "netWorth": {"type": "number", "minimum": 0, "maximum": 10000000}
        },
        "required": ["username", "email", "password", "firstName", "lastName", "isAccountOwner", "accountId"]
    }
)
async def create_user(
    username: str,
    email: str,
    password: str,
    firstName: str,
    lastName: str,
    isAccountOwner: bool,
    accountId: str,
    gender: Optional[str] = None,
    role: Optional[str] = None,
    dob: Optional[str] = None,
    netWorth: Optional[float] = None
) -> Dict[str, Any]:
    """Create user - calls same DocumentManager method as REST"""

    db = DatabaseFactory.get_instance()

    # Build user data
    user_data = {
        "username": username,
        "email": email,
        "password": password,
        "firstName": firstName,
        "lastName": lastName,
        "isAccountOwner": isAccountOwner,
        "accountId": accountId
    }

    # Add optional fields
    if gender:
        user_data["gender"] = gender
    if role:
        user_data["role"] = role
    if dob:
        user_data["dob"] = dob
    if netWorth is not None:
        user_data["netWorth"] = netWorth

    # Create user (validation happens in DocumentManager via Pydantic)
    result = await db.create("User", user_data)

    return {"user": result}


def get_all_tools() -> List[Dict]:
    """Get all registered tools"""
    return registry.get_all()
```

#### Task 2.2: Test with Claude Desktop

**Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "events-api": {
      "command": "python",
      "args": ["/Users/markmalamut/Projects/events/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/Users/markmalamut/Projects/events"
      }
    }
  }
}
```

**Test queries:**
```
1. "List all users"
2. "Show me users with username containing 'mark'"
3. "Create a test user named John Doe"
4. "Get user usr_001"
5. "Show users sorted by creation date"
```

**Success criteria:**
- [x] All 3 tools work
- [x] Validation errors returned properly
- [x] Same results as REST API
- [x] Claude can parse responses

**Deliverable**: Working MCP server with 3 User tools, tested in Claude Desktop.

---

## Phase 2: Auto-Generation (2 days)

### Goal
Generate all CRUD tools for all 8 entities using metadata, plus auth tools.

### Day 3: Schema Auto-Generation

#### Task 3.1: Create Schema Generator (`app/mcp/schemas.py`)
```python
"""
Auto-generate MCP tool schemas from entity metadata.
"""
from typing import Dict, List, Any
from app.services.metadata import MetadataService


def generate_list_tool_schema(entity_name: str) -> Dict[str, Any]:
    """Generate schema for list_{entity} tool"""
    metadata = MetadataService.get(entity_name)
    fields = metadata.get("fields", {})

    # Build filter properties from metadata
    filter_props = {}
    sort_enum = []

    for field_name, field_meta in fields.items():
        # Add to filter properties
        filter_props[field_name] = _convert_field_to_filter_schema(field_name, field_meta)

        # Add to sort enum (all fields are sortable)
        sort_enum.append(field_name)

    return {
        "type": "object",
        "properties": {
            "filter": {
                "type": "object",
                "description": f"Filter {entity_name} by field values (supports MongoDB operators)",
                "properties": filter_props
            },
            "filter_matching": {
                "type": "string",
                "enum": ["exact", "contains", "fuzzy"],
                "default": "exact",
                "description": "String matching strategy (MongoDB only)"
            },
            "sort": {
                "type": "array",
                "description": "Sort specification",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "enum": sort_enum},
                        "direction": {"type": "string", "enum": ["asc", "desc"]}
                    },
                    "required": ["field", "direction"]
                }
            },
            "page": {"type": "integer", "minimum": 1, "default": 1},
            "pageSize": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
            "view": {
                "type": "object",
                "description": "Select specific fields from related entities"
            }
        }
    }


def generate_get_tool_schema(entity_name: str) -> Dict[str, Any]:
    """Generate schema for get_{entity} tool"""
    return {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": f"{entity_name} ID"
            }
        },
        "required": ["id"]
    }


def generate_create_tool_schema(entity_name: str) -> Dict[str, Any]:
    """Generate schema for create_{entity} tool"""
    metadata = MetadataService.get(entity_name)
    fields = metadata.get("fields", {})

    properties = {}
    required = []

    for field_name, field_meta in fields.items():
        # Skip auto-generated fields
        if field_meta.get("autoGenerate") or field_meta.get("autoUpdate"):
            continue

        # Skip id (auto-generated)
        if field_name == "id":
            continue

        # Convert field to schema
        properties[field_name] = _convert_field_to_input_schema(field_name, field_meta)

        # Track required fields
        if field_meta.get("required"):
            required.append(field_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required
    }


def generate_update_tool_schema(entity_name: str) -> Dict[str, Any]:
    """Generate schema for update_{entity} tool"""
    metadata = MetadataService.get(entity_name)
    fields = metadata.get("fields", {})

    properties = {
        "id": {
            "type": "string",
            "description": f"{entity_name} ID to update"
        }
    }

    for field_name, field_meta in fields.items():
        # Skip auto-generated and auto-update fields
        if field_meta.get("autoGenerate") or field_meta.get("autoUpdate"):
            continue

        # Skip id (it's the key)
        if field_name == "id":
            continue

        # All fields optional in update
        properties[field_name] = _convert_field_to_input_schema(field_name, field_meta)

    return {
        "type": "object",
        "properties": properties,
        "required": ["id"]
    }


def generate_delete_tool_schema(entity_name: str) -> Dict[str, Any]:
    """Generate schema for delete_{entity} tool"""
    return {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": f"{entity_name} ID to delete"
            }
        },
        "required": ["id"]
    }


def _convert_field_to_filter_schema(field_name: str, field_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Convert field metadata to filter schema (supports MongoDB operators)"""
    field_type = field_meta.get("type", "String")

    # Base type
    base_schema = _convert_field_to_input_schema(field_name, field_meta)

    # For numeric/date types, support MongoDB operators
    if field_type in ["Integer", "Number", "Currency", "Date", "Datetime"]:
        return {
            "oneOf": [
                base_schema,  # Simple equality
                {
                    "type": "object",
                    "description": f"MongoDB query operators for {field_name}",
                    "properties": {
                        "$gte": {**base_schema, "description": "Greater than or equal"},
                        "$lte": {**base_schema, "description": "Less than or equal"},
                        "$gt": {**base_schema, "description": "Greater than"},
                        "$lt": {**base_schema, "description": "Less than"},
                        "$ne": {**base_schema, "description": "Not equal"},
                        "$in": {
                            "type": "array",
                            "items": base_schema,
                            "description": "In array"
                        }
                    }
                }
            ]
        }

    return base_schema


def _convert_field_to_input_schema(field_name: str, field_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Convert field metadata to input schema"""
    field_type = field_meta.get("type", "String")

    # Type mapping
    type_map = {
        "String": "string",
        "Integer": "integer",
        "Number": "number",
        "Boolean": "boolean",
        "Currency": "number",
        "Date": "string",
        "Datetime": "string",
        "ObjectId": "string"
    }

    schema = {"type": type_map.get(field_type, "string")}

    # Add format for dates
    if field_type == "Date":
        schema["format"] = "date"
    elif field_type == "Datetime":
        schema["format"] = "date-time"

    # Add string constraints
    if field_type == "String":
        if "min_length" in field_meta:
            schema["minLength"] = field_meta["min_length"]
        if "max_length" in field_meta:
            schema["maxLength"] = field_meta["max_length"]
        if "pattern" in field_meta and "regex" in field_meta["pattern"]:
            schema["pattern"] = field_meta["pattern"]["regex"]

    # Add numeric constraints
    if field_type in ["Integer", "Number", "Currency"]:
        if "ge" in field_meta:
            schema["minimum"] = field_meta["ge"]
        if "le" in field_meta:
            schema["maximum"] = field_meta["le"]

    # Add enum constraints
    if "enum" in field_meta and "values" in field_meta["enum"]:
        schema["enum"] = field_meta["enum"]["values"]
        if "message" in field_meta["enum"]:
            schema["description"] = field_meta["enum"]["message"]

    return schema


def get_all_entities() -> List[str]:
    """Get all entity names"""
    return MetadataService.list_entities()
```

#### Task 3.2: Create Generic Tool Generator (`app/mcp/registry.py`)
```python
"""
Tool registry that auto-generates CRUD tools for all entities.
"""
from typing import Dict, List, Any, Optional
from app.db import DatabaseFactory
from app.services.metadata import MetadataService
from .schemas import (
    generate_list_tool_schema,
    generate_get_tool_schema,
    generate_create_tool_schema,
    generate_update_tool_schema,
    generate_delete_tool_schema,
    get_all_entities
)


class MCPToolRegistry:
    """Registry for auto-generated MCP tools"""

    def __init__(self):
        self.tools = []

    def generate_crud_tools_for_entity(self, entity_name: str):
        """Generate all CRUD tools for an entity"""
        entity_lower = entity_name.lower()

        # 1. list_{entity}s tool
        self._add_tool(
            name=f"list_{entity_lower}s",
            description=f"List {entity_name} entities with filtering, sorting, and pagination",
            input_schema=generate_list_tool_schema(entity_name),
            handler=self._create_list_handler(entity_name)
        )

        # 2. get_{entity} tool
        self._add_tool(
            name=f"get_{entity_lower}",
            description=f"Get a single {entity_name} by ID",
            input_schema=generate_get_tool_schema(entity_name),
            handler=self._create_get_handler(entity_name)
        )

        # 3. create_{entity} tool
        self._add_tool(
            name=f"create_{entity_lower}",
            description=f"Create a new {entity_name}",
            input_schema=generate_create_tool_schema(entity_name),
            handler=self._create_create_handler(entity_name)
        )

        # 4. update_{entity} tool
        self._add_tool(
            name=f"update_{entity_lower}",
            description=f"Update an existing {entity_name}",
            input_schema=generate_update_tool_schema(entity_name),
            handler=self._create_update_handler(entity_name)
        )

        # 5. delete_{entity} tool
        self._add_tool(
            name=f"delete_{entity_lower}",
            description=f"Delete a {entity_name} by ID",
            input_schema=generate_delete_tool_schema(entity_name),
            handler=self._create_delete_handler(entity_name)
        )

    def generate_all_crud_tools(self):
        """Generate CRUD tools for all entities"""
        for entity_name in get_all_entities():
            self.generate_crud_tools_for_entity(entity_name)

    def _add_tool(self, name: str, description: str, input_schema: Dict, handler):
        """Add a tool to registry"""
        self.tools.append({
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": handler
        })

    def _create_list_handler(self, entity_name: str):
        """Create list handler for entity"""
        async def handler(
            filter: Optional[Dict] = None,
            filter_matching: str = "exact",
            sort: Optional[List[Dict]] = None,
            page: int = 1,
            pageSize: int = 25,
            view: Optional[Dict] = None
        ) -> Dict[str, Any]:
            db = DatabaseFactory.get_instance()

            result = await db.get_all(
                entity_name=entity_name,
                filters=filter,
                filter_matching=filter_matching,
                sort_by=sort,
                page=page,
                page_size=pageSize,
                view_spec=view
            )

            return {
                "data": result["data"],
                "pagination": result.get("pagination", {}),
                "total": result.get("pagination", {}).get("totalRecords", 0)
            }

        return handler

    def _create_get_handler(self, entity_name: str):
        """Create get handler for entity"""
        async def handler(id: str) -> Dict[str, Any]:
            db = DatabaseFactory.get_instance()

            result = await db.get_by_id(entity_name, id)

            if not result:
                raise ValueError(f"{entity_name} {id} not found")

            return {"data": result}

        return handler

    def _create_create_handler(self, entity_name: str):
        """Create create handler for entity"""
        async def handler(**kwargs) -> Dict[str, Any]:
            db = DatabaseFactory.get_instance()

            # Validation happens in DocumentManager via Pydantic
            result = await db.create(entity_name, kwargs)

            return {"data": result}

        return handler

    def _create_update_handler(self, entity_name: str):
        """Create update handler for entity"""
        async def handler(id: str, **kwargs) -> Dict[str, Any]:
            db = DatabaseFactory.get_instance()

            # Validation happens in DocumentManager via Pydantic
            result = await db.update(entity_name, id, kwargs)

            if not result:
                raise ValueError(f"{entity_name} {id} not found")

            return {"data": result}

        return handler

    def _create_delete_handler(self, entity_name: str):
        """Create delete handler for entity"""
        async def handler(id: str) -> Dict[str, Any]:
            db = DatabaseFactory.get_instance()

            result = await db.delete(entity_name, id)

            if not result:
                raise ValueError(f"{entity_name} {id} not found")

            return {"success": True, "id": id}

        return handler

    def get_all_tools(self) -> List[Dict]:
        """Get all registered tools"""
        return self.tools


# Global registry instance
_registry = MCPToolRegistry()


def get_registry() -> MCPToolRegistry:
    """Get global registry instance"""
    return _registry
```

#### Task 3.3: Update Server to Use Registry

Update `app/mcp/server.py`:
```python
from .registry import get_registry

class EventsMCPServer:
    # ... existing code ...

    def register_tools(self):
        """Register all MCP tools"""
        # Generate all CRUD tools
        registry = get_registry()
        registry.generate_all_crud_tools()

        # Register with MCP server
        for tool in registry.get_all_tools():
            self.server.add_tool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["input_schema"],
                handler=tool["handler"]
            )
```

**Success criteria:**
- [x] 40 CRUD tools generated (5 per entity × 8 entities)
- [x] All schemas auto-generated from metadata
- [x] All tools work with Claude Desktop
- [x] Complex queries work (filters, operators, sort)

**Deliverable**: Auto-generated CRUD tools for all 8 entities.

---

### Day 4: Service Provider Tools (Auth)

#### Task 4.1: Create Auth Tools (`app/mcp/auth.py`)
```python
"""
Authentication tools for MCP.
Uses token-based auth instead of cookies.
"""
from typing import Dict, Any, Optional
import uuid
from app.providers.auth.cookies.redis_provider import CookiesAuth
from app.db import DatabaseFactory


class MCPAuth:
    """Token-based auth for MCP (wraps CookiesAuth)"""

    @classmethod
    async def initialize(cls):
        """Initialize auth (reuse CookiesAuth Redis store)"""
        from app.config import Config
        redis_config = Config.get("auth.cookies.redis", {})
        await CookiesAuth.initialize(redis_config)

    @classmethod
    async def login(cls, entity_name: str, username: str, password: str) -> Dict[str, Any]:
        """
        Login and return token.
        Reuses CookiesAuth logic but returns token instead of setting cookie.
        """
        # Build credentials dict
        credentials = {"username": username, "password": password}

        # Use CookiesAuth login method
        auth = CookiesAuth()
        session_id = await auth.login(entity_name, credentials)

        if not session_id:
            raise ValueError("Invalid username or password")

        return {
            "success": True,
            "token": session_id,
            "message": "Login successful"
        }

    @classmethod
    async def logout(cls, token: str) -> Dict[str, Any]:
        """Logout and invalidate token"""
        auth = CookiesAuth()

        if auth.cookie_store:
            await auth.cookie_store.delete_session(token)

        return {
            "success": True,
            "message": "Logout successful"
        }

    @classmethod
    async def refresh(cls, token: str) -> Dict[str, Any]:
        """Refresh token TTL"""
        auth = CookiesAuth()

        if not auth.cookie_store:
            raise ValueError("Auth not initialized")

        session = await auth.cookie_store.get_session(token)
        if not session:
            raise ValueError("Invalid or expired token")

        # Renew session
        from app.providers.auth.cookies.redis_provider import SESSION_TTL
        await auth.cookie_store.renew_session(token, session, SESSION_TTL)

        return {
            "success": True,
            "message": "Token refreshed"
        }

    @classmethod
    async def validate_token(cls, token: str) -> bool:
        """Validate a token"""
        auth = CookiesAuth()

        if not auth.cookie_store:
            return False

        session = await auth.cookie_store.get_session(token)
        return bool(session)


async def initialize_auth():
    """Initialize auth system"""
    await MCPAuth.initialize()


# Add auth tools to registry
def register_auth_tools(registry):
    """Register auth tools with MCP registry"""

    # user_auth_login
    registry._add_tool(
        name="user_auth_login",
        description="Login to User account and receive authentication token",
        input_schema={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Username (from User.username field)"
                },
                "password": {
                    "type": "string",
                    "description": "Password (from User.password field)"
                }
            },
            "required": ["username", "password"]
        },
        handler=lambda username, password: MCPAuth.login("User", username, password)
    )

    # user_auth_logout
    registry._add_tool(
        name="user_auth_logout",
        description="Logout and invalidate authentication token",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token from login"
                }
            },
            "required": ["token"]
        },
        handler=lambda token: MCPAuth.logout(token)
    )

    # user_auth_refresh
    registry._add_tool(
        name="user_auth_refresh",
        description="Refresh authentication token TTL",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token from login"
                }
            },
            "required": ["token"]
        },
        handler=lambda token: MCPAuth.refresh(token)
    )
```

#### Task 4.2: Update Server to Register Auth Tools

Update `app/mcp/server.py`:
```python
from .auth import register_auth_tools

class EventsMCPServer:
    # ... existing code ...

    def register_tools(self):
        """Register all MCP tools"""
        registry = get_registry()

        # Generate all CRUD tools
        registry.generate_all_crud_tools()

        # Add auth tools
        register_auth_tools(registry)

        # Register with MCP server
        for tool in registry.get_all_tools():
            self.server.add_tool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["input_schema"],
                handler=tool["handler"]
            )
```

**Success criteria:**
- [x] 3 auth tools work (login, logout, refresh)
- [x] Token returned on login
- [x] Token validated in subsequent calls
- [x] Same Redis store as REST API

**Deliverable**: Auth tools working with token-based authentication.

---

## Phase 3: Polish (2 days)

### Goal
Make MCP server production-ready with error handling, documentation, and testing.

### Day 5: Error Handling & Validation

#### Task 5.1: Add Error Handling Wrapper (`app/mcp/utils.py`)
```python
"""
Utilities for MCP tools.
"""
from typing import Callable, Any
from functools import wraps
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors in MCP tool handlers.
    Converts exceptions to user-friendly messages.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)

        except ValidationError as e:
            # Pydantic validation error
            errors = []
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                message = error["msg"]
                errors.append(f"{field}: {message}")

            logger.error(f"Validation error in {func.__name__}: {errors}")

            return {
                "error": "Validation failed",
                "details": errors
            }

        except ValueError as e:
            # Business logic error (e.g., "User not found")
            logger.error(f"Value error in {func.__name__}: {str(e)}")

            return {
                "error": str(e)
            }

        except Exception as e:
            # Unexpected error
            logger.exception(f"Unexpected error in {func.__name__}")

            return {
                "error": "Internal server error",
                "message": str(e)
            }

    return wrapper
```

#### Task 5.2: Apply Error Handling to Tools

Update `app/mcp/registry.py` to wrap handlers:
```python
from .utils import handle_errors

class MCPToolRegistry:
    # ... existing code ...

    def _create_list_handler(self, entity_name: str):
        """Create list handler for entity"""
        @handle_errors
        async def handler(...):
            # ... existing code ...

        return handler

    # Apply to all handlers: get, create, update, delete
```

#### Task 5.3: Add Logging

Update `app/mcp/server.py`:
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EventsMCPServer:
    async def initialize(self):
        # ... existing code ...
        logger.info(f"Initialized database: {db_type}")
        logger.info(f"Initialized {len(entities)} entities")

    def register_tools(self):
        # ... existing code ...
        logger.info(f"Registered {len(registry.get_all_tools())} MCP tools")
```

**Success criteria:**
- [x] Pydantic validation errors formatted clearly
- [x] Business logic errors (404, etc.) handled
- [x] Unexpected errors caught and logged
- [x] All errors user-friendly

**Deliverable**: Robust error handling for all tools.

---

### Day 6: Documentation & Testing

#### Task 6.1: Create Documentation

**docs/mcp/setup.md**:
```markdown
# MCP Server Setup

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Claude Desktop:

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "events-api": {
      "command": "python",
      "args": ["/path/to/events/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/path/to/events"
      }
    }
  }
}
```

3. Restart Claude Desktop

4. Verify connection:
Ask Claude: "List available MCP tools"

## Configuration

MCP server uses same config as REST API:
- `mongo.json` - MongoDB configuration
- `es.json` - Elasticsearch configuration
- `sqlite.json` - SQLite configuration

## Running Standalone

```bash
python mcp_server.py
```

## Troubleshooting

Check logs:
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```
```

**docs/mcp/tools.md**:
Auto-generate tool reference from schemas.

**docs/mcp/examples.md**:
Common query examples.

#### Task 6.2: Create Tests

**tests/mcp/test_tools.py**:
```python
import pytest
from app.mcp.registry import MCPToolRegistry
from app.db import DatabaseFactory

@pytest.fixture
async def setup_db():
    # Initialize database
    await DatabaseFactory.initialize("mongodb", "localhost", "test_db")
    yield
    await DatabaseFactory.close()

@pytest.mark.asyncio
async def test_list_users(setup_db):
    registry = MCPToolRegistry()
    registry.generate_crud_tools_for_entity("User")

    # Get list_users handler
    tool = next(t for t in registry.get_all_tools() if t["name"] == "list_users")
    handler = tool["handler"]

    # Call handler
    result = await handler(page=1, pageSize=10)

    assert "data" in result
    assert "pagination" in result
    assert isinstance(result["data"], list)

# ... more tests ...
```

**Success criteria:**
- [x] Setup documentation complete
- [x] Tool reference generated
- [x] Example queries documented
- [x] Unit tests for key tools
- [x] Integration tests pass

**Deliverable**: Production-ready MCP server with full documentation.

---

## Testing Strategy

### Unit Tests
- Schema generation correctness
- Tool handler logic
- Error handling
- Auth token validation

### Integration Tests
- Database queries return correct data
- Validation works same as REST
- FK checks enforced
- Pagination works

### End-to-End Tests with Claude Desktop
- All 43 tools work (40 CRUD + 3 auth)
- Complex queries with operators
- Multi-step workflows (create → update → delete)
- Error messages clear

---

## Deployment

### Development
```bash
# Run MCP server
python mcp_server.py
```

### Production

**Option 1: Systemd Service**
```ini
[Unit]
Description=Events MCP Server
After=network.target

[Service]
Type=simple
User=events
WorkingDirectory=/opt/events
Environment="PYTHONPATH=/opt/events"
ExecStart=/usr/bin/python3 /opt/events/mcp_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Option 2: Docker**
```dockerfile
FROM python:3.12
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "mcp_server.py"]
```

---

## Success Metrics

### Phase 1
- [x] MCP server starts and connects to database
- [x] 3 basic tools work (list, get, create)
- [x] Claude Desktop connects successfully
- [x] Same results as REST API

### Phase 2
- [x] 40 CRUD tools auto-generated (8 entities × 5 ops)
- [x] 3 auth tools work (login, logout, refresh)
- [x] Complex queries work (MongoDB operators)
- [x] All schemas from metadata

### Phase 3
- [x] Error handling comprehensive
- [x] Documentation complete
- [x] Tests passing
- [x] Performance < 500ms per tool call

---

## Performance Considerations

### Expected Performance
- Tool call latency: < 500ms
- Database queries: Same as REST (reuses DocumentManager)
- Pagination: Same as REST
- Memory: +50MB for MCP server process

### Optimization Opportunities
- Connection pooling (already in DocumentManager)
- Schema caching (generate once at startup)
- Response caching (for frequently accessed data)

---

## Maintenance

### Adding New Entity
1. Add entity to schema.yaml
2. Generate model: `make models`
3. Restart MCP server
4. **Done** - 5 CRUD tools auto-generated

### Adding New Service
1. Create provider class with `@expose_endpoint`
2. Add to providers_registry.json
3. Add to entity metadata (services section)
4. Add service tool registration in `auth.py` pattern
5. Restart MCP server

### Updating Field Metadata
1. Update schema.yaml
2. Regenerate models: `make models`
3. Restart MCP server
4. **Done** - Tool schemas auto-update

---

## Rollback Plan

If MCP has issues:

1. **Stop MCP server** (doesn't affect REST)
2. **Remove from Claude Desktop config**
3. **REST API continues working** (unchanged)

No risk to production REST API.

---

## Future Enhancements

### Phase 4 (Optional)
- Resources API (entity data as MCP resources)
- Sampling support (example data for discovery)
- Batch operations (bulk create/update)
- Advanced filtering (full-text search)
- Real-time notifications (when MCP 2.0 supports)

### Phase 5 (Optional)
- Additional transports (SSE, WebSocket)
- Multi-tenant support
- Rate limiting
- Audit logging

---

## Questions & Support

- See `mcp.md` for architecture overview
- See `mcp_fit.md` for fit analysis
- See `docs/mcp/` for detailed documentation

---

## Timeline Summary

| Phase | Days | Deliverable |
|-------|------|-------------|
| Phase 1 | 2 | Basic MCP server + 3 tools |
| Phase 2 | 2 | Auto-generated 40 CRUD + 3 auth tools |
| Phase 3 | 2 | Production-ready with docs & tests |
| **Total** | **6 days** | **Production MCP server** |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MCP SDK bugs | Low | Medium | Use stable version, test thoroughly |
| Claude Desktop issues | Low | Low | Test with multiple clients |
| Performance problems | Low | Medium | Same backend as REST (proven) |
| Auth complexity | Medium | Medium | Token-based simpler than cookies |
| Breaking REST | None | High | Zero changes to REST code |

---

## Conclusion

This plan delivers a production-ready MCP server in 6 days with:
- ✅ Zero changes to existing codebase
- ✅ Auto-generated tools from metadata
- ✅ Same business logic as REST
- ✅ Comprehensive error handling
- ✅ Full documentation
- ✅ Low risk, high value

The metadata-driven architecture makes this implementation straightforward and maintainable.
