# MCP (Model Context Protocol) Integration

## Overview

This document describes how to add MCP support to the Events API as a complementary interface alongside the existing REST API.

## What is MCP?

**Model Context Protocol (MCP)** is a standardized protocol developed by Anthropic that enables AI assistants to:
- Access data from external sources (databases, APIs, file systems)
- Execute tools and functions
- Maintain context across interactions

### Key Components

- **MCP Server**: Exposes resources (data) and tools (functions) via standardized protocol
- **MCP Client**: Connects to MCP servers (Claude Desktop, IDEs, etc.)
- **Transport**: Communication layer (stdio, SSE, WebSocket)

## Architecture: Hybrid REST + MCP

```
┌─────────────┐      ┌─────────────┐
│ REST Router │      │ MCP Server  │  ← New layer (thin wrapper)
└──────┬──────┘      └──────┬──────┘
       │                    │
       ├─→ endpoint_handlers│─→ mcp_tools.py
       │                    │
       └────────────┬───────┘
                    ↓
          ┌────────────────┐
          │ DocumentManager│ ← No changes - reused by both
          │  - MongoDB     │
          │  - Elasticsearch│
          │  - SQLite      │
          └────────┬───────┘
                   │
                   ↓
              ┌────────┐
              │   DB   │
              └────────┘
```

**Key principle**: MCP is an additional interface, not a replacement. Both REST and MCP call the same business logic layer.

## Current REST API → MCP Mapping

### REST Request Example
```http
GET /api/User?filter=username:mark&filter_matching=exact&sort=createdAt:desc&page=1&pageSize=10
```

### Equivalent MCP Tool Call
```json
{
  "name": "list_users",
  "arguments": {
    "filter": {"username": "mark"},
    "filter_matching": "exact",
    "sort": [{"field": "createdAt", "direction": "desc"}],
    "page": 1,
    "pageSize": 10
  }
}
```

### Parameter Mapping

| REST Param | MCP Tool Argument | Type | Description |
|------------|------------------|------|-------------|
| `filter=field:value` | `filter: {field: value}` | Object | Field filters |
| `filter_matching=exact` | `filter_matching: "exact"` | Enum | Match strategy (exact/contains/fuzzy) |
| `sort=field:desc` | `sort: [{field, direction}]` | Array | Sort specification |
| `page=1` | `page: 1` | Integer | Page number |
| `pageSize=10` | `pageSize: 10` | Integer | Results per page |
| `view=account(id,name)` | `view: {account: ["id","name"]}` | Object | Field selection |

**Conclusion**: Current REST API parameters are already MCP-ready. No redesign needed.

## Natural Language Query Conversion

MCP doesn't do NL parsing - the AI assistant (Claude) handles conversion:

```
┌─────────────────────────────────────────────────┐
│ User: "Show me users named Mark from last week" │
└────────────────────┬────────────────────────────┘
                     ↓
          ┌──────────────────────┐
          │ Claude analyzes NL   │
          │ + reads tool schemas │
          └──────────┬───────────┘
                     ↓
          ┌──────────────────────┐
          │ Claude generates:    │
          │ {                    │
          │   "name": "list_users",│
          │   "arguments": {     │
          │     "filter": {      │
          │       "username": "mark",│
          │       "createdAt": { │
          │         "$gte": "2025-10-16"│
          │       }              │
          │     },               │
          │     "filter_matching": "contains"│
          │   }                  │
          │ }                    │
          └──────────┬───────────┘
                     ↓
          ┌──────────────────────┐
          │ MCP Server executes  │
          │ (calls DocumentMgr)  │
          └──────────┬───────────┘
                     ↓
          ┌──────────────────────┐
          │ Returns results      │
          └──────────┬───────────┘
                     ↓
          ┌──────────────────────┐
          │ Claude formats:      │
          │ "I found 3 users..." │
          └──────────────────────┘
```

**Key insight**: Tool schema quality determines NL conversion quality. Our metadata-driven architecture makes this easy.

## MCP Tool Schema Generation

### Leveraging Existing Metadata

Our `schema.yaml` → model metadata already contains everything needed for MCP schemas:

```python
# Metadata we already have:
{
  "username": {
    "type": "String",
    "required": True,
    "min_length": 3,
    "max_length": 50
  },
  "gender": {
    "type": "String",
    "enum": {"values": ["male", "female", "other"]}
  },
  "netWorth": {
    "type": "Currency",
    "ge": 0,
    "le": 10000000
  }
}
```

### Auto-Generated MCP Schema

```python
def generate_mcp_tool_schema(entity_name):
    """Generate MCP tool schema from entity metadata"""
    metadata = MetadataService.get(entity_name)
    fields = metadata['fields']

    # Build filter properties from metadata
    filter_props = {}
    sort_enum = []

    for field_name, field_meta in fields.items():
        # Add to filter properties
        filter_props[field_name] = convert_field_to_mcp_schema(field_meta)

        # Add to sort enum
        sort_enum.append(field_name)

    return {
        "name": f"list_{entity_name.lower()}s",
        "description": f"List {entity_name} entities with filtering, sorting, and pagination",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "object",
                    "description": f"Filter {entity_name} by field values",
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
                        }
                    }
                },
                "page": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1,
                    "description": "Page number"
                },
                "pageSize": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 25,
                    "description": "Results per page"
                },
                "view": {
                    "type": "object",
                    "description": "Select specific fields from related entities"
                }
            }
        }
    }

def convert_field_to_mcp_schema(field_meta):
    """Convert field metadata to MCP parameter schema"""
    field_type = field_meta.get("type", "String")

    # Base type mapping
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
    if field_type in ["Date", "Datetime"]:
        schema["format"] = "date-time"

    # Add enum constraints
    if "enum" in field_meta:
        schema["enum"] = field_meta["enum"]["values"]
        schema["description"] = field_meta["enum"].get("message", "")

    # Add numeric constraints
    if "ge" in field_meta:
        schema["minimum"] = field_meta["ge"]
    if "le" in field_meta:
        schema["maximum"] = field_meta["le"]

    # MongoDB query operators for ranges
    if field_type in ["Integer", "Number", "Currency", "Date", "Datetime"]:
        schema = {
            "oneOf": [
                schema,  # Simple equality
                {
                    "type": "object",
                    "properties": {
                        "$gte": schema.copy(),
                        "$lte": schema.copy(),
                        "$gt": schema.copy(),
                        "$lt": schema.copy(),
                        "$in": {"type": "array", "items": schema.copy()}
                    }
                }
            ]
        }

    return schema
```

## MCP Tool Implementation

### Example: list_users Tool

```python
# app/mcp/tools.py
from app.db import DatabaseFactory
from app.services.metadata import MetadataService

async def list_users_tool(
    filter: dict = None,
    filter_matching: str = "exact",
    sort: list = None,
    page: int = 1,
    pageSize: int = 25,
    view: dict = None
):
    """
    MCP tool for listing users.
    Reuses exact same DocumentManager as REST endpoint.
    """

    # Get database instance (same as REST)
    db = DatabaseFactory.get_instance()

    # Call same method REST uses
    result = await db.get_all(
        entity_name="User",
        filters=filter,
        filter_matching=filter_matching,
        sort_by=sort,
        page=page,
        page_size=pageSize,
        view_spec=view
    )

    # Return in MCP format (same structure as REST)
    return {
        "data": result["data"],
        "pagination": result.get("pagination", {})
    }
```

### Example: create_user Tool

```python
async def create_user_tool(
    username: str,
    email: str,
    password: str,
    firstName: str,
    lastName: str,
    isAccountOwner: bool,
    accountId: str,
    gender: str = None,
    role: str = None,
    dob: str = None,
    netWorth: float = None
):
    """MCP tool for creating a user"""

    db = DatabaseFactory.get_instance()

    # Build entity data
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

    # Use same create method as REST
    result = await db.create("User", user_data)

    return {"data": result}
```

## CRUD Tools per Entity

For each entity, generate 5 standard tools:

1. **list_{entity}s** - Get collection with filters/sort/pagination
2. **get_{entity}** - Get single entity by ID
3. **create_{entity}** - Create new entity
4. **update_{entity}** - Update existing entity
5. **delete_{entity}** - Delete entity by ID

All auto-generated from metadata using the patterns above.

## MongoDB Query Operators in MCP

Claude understands MongoDB query syntax natively:

**User asks**: "Find users with net worth between 100k and 500k"

**Claude generates**:
```json
{
  "name": "list_users",
  "arguments": {
    "filter": {
      "netWorth": {
        "$gte": 100000,
        "$lte": 500000
      }
    }
  }
}
```

**User asks**: "Show admins or read-only users"

**Claude generates**:
```json
{
  "filter": {
    "role": {
      "$in": ["admin", "read"]
    }
  }
}
```

Our DocumentManager already handles these operators, so no changes needed.

## Dynamic Service Providers in MCP

The `@expose_endpoint` pattern for services (like auth) can also be exposed as MCP tools:

```python
# Service endpoint metadata → MCP tool
@expose_endpoint(method="POST", route="/login", summary="Login")
async def login(entity_name: str, credentials: dict) -> str | None:
    ...

# Becomes MCP tool:
{
  "name": "user_auth_login",
  "description": "Login to User account",
  "inputSchema": {
    "type": "object",
    "properties": {
      "username": {"type": "string"},
      "password": {"type": "string"}
    },
    "required": ["username", "password"]
  }
}
```

Service tools follow pattern: `{entity}_{category}_{method}` (e.g., `user_auth_login`, `user_auth_logout`)

## Advantages of MCP Addition

### For AI Assistants
- Direct database queries via natural language
- No need to learn REST API structure
- Context-aware multi-step operations
- Automatic pagination handling

### For Developers
- Reuse 100% of existing backend logic
- Auto-generated tools from metadata
- No duplicate validation/business logic
- Consistent behavior with REST API

### For Users
- Natural language data access
- Complex queries without writing code
- AI-assisted data analysis
- Automated workflows

## What Doesn't Need to Change

✅ **No changes required to:**
- `app/db/document_manager.py` - Core database abstraction
- `app/db/mongodb/documents.py` - MongoDB implementation
- `app/db/elasticsearch/documents.py` - Elasticsearch implementation
- `app/db/sqlite/documents.py` - SQLite implementation
- `app/models/*_model.py` - Pydantic models
- `app/services/metadata.py` - Metadata service
- `app/services/model.py` - Model service
- Business logic, validations, FK checks, etc.

## What to Add

📁 **New files needed:**
```
app/mcp/
  ├── __init__.py
  ├── server.py          # MCP server setup
  ├── tools.py           # Tool implementations (thin wrappers)
  ├── schemas.py         # Auto-generate tool schemas from metadata
  └── registry.py        # Register all tools
```

**Estimated effort**: ~1 week
- Core MCP server: 2-3 days
- Tool generation from metadata: 1-2 days
- Testing: 1-2 days

## Use Cases

### Use Case 1: Data Analysis
```
User: "What's the average net worth of female users created this year?"
  ↓
Claude calls: list_users(filter={gender: "female", createdAt: {$gte: "2025-01-01"}})
  ↓
Claude processes results and calculates average
  ↓
Claude: "The average net worth is $245,000 across 47 female users"
```

### Use Case 2: Complex Queries
```
User: "Find all account owners in the system who have a profile"
  ↓
Claude calls: list_users(filter={isAccountOwner: true}, view={profile: ["id"]})
  ↓
Claude filters results with profiles
  ↓
Claude: "Found 12 account owners with profiles: [list]"
```

### Use Case 3: Batch Operations
```
User: "Create 5 test users in the marketing account"
  ↓
Claude calls: create_user(...) 5 times with variations
  ↓
Claude: "Created 5 test users: test_user_1 through test_user_5"
```

## MCP vs REST: When to Use Each

| Scenario | Use REST | Use MCP |
|----------|----------|---------|
| Web/mobile UI | ✅ | ❌ |
| Third-party integrations | ✅ | ❌ |
| Public API | ✅ | ❌ |
| Webhooks/callbacks | ✅ | ❌ |
| AI assistant queries | ❌ | ✅ |
| Natural language data access | ❌ | ✅ |
| Claude Desktop integration | ❌ | ✅ |
| Automated data analysis | ❌ | ✅ |
| IDE integrations | ❌ | ✅ |

## Recommendation

**Implement hybrid approach:**
- Keep REST API for traditional clients (web, mobile, integrations)
- Add MCP server for AI assistant access
- Share all backend logic between both interfaces
- Auto-generate MCP tools from existing metadata

This gives you the best of both worlds with minimal duplication.

## Next Steps

1. Install MCP Python SDK: `pip install mcp`
2. Create basic MCP server in `app/mcp/server.py`
3. Implement 1-2 tools as proof of concept
4. Auto-generate remaining tools from metadata
5. Test with Claude Desktop
6. Document MCP server connection details for users

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude MCP Documentation](https://docs.anthropic.com/en/docs/agents-and-tools/mcp)
