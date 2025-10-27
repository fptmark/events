# MCP Server Testing Guide

## Implementation Complete ✓

MCP server with **37 auto-generated tools** for all 8 entities is ready for testing.

## Quick Start

### 1. Run Unit Tests

```bash
python test_mcp.py
```

This verifies:
- Server imports correctly
- Tool registry works
- All 37 tools are registered with proper schemas
- Schema generator reads from schema.yaml correctly

### 2. Test with Claude Desktop

#### Configure Claude Desktop

Add the MCP server to Claude Desktop configuration:

```bash
# Mac/Linux
cat claude_desktop_config.json >> ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or manually edit:
# ~/Library/Application Support/Claude/claude_desktop_config.json
```

Configuration:
```json
{
  "mcpServers": {
    "events-api": {
      "command": "python",
      "args": [
        "/Users/markmalamut/Projects/events/mcp_server.py"
      ],
      "env": {
        "MCP_CONFIG": "/Users/markmalamut/Projects/events/mongo.json"
      }
    }
  }
}
```

#### Start the Server

The server starts automatically when Claude Desktop connects.

You can also test it manually:

```bash
# Make sure MongoDB is running
python mcp_server.py
```

#### Test Queries

In Claude Desktop, try these natural language queries:

1. **List Entities**
   - "List all users"
   - "Show me recent events"
   - "Find accounts that expired"

2. **Get Entity**
   - "Get user with ID [user-id]"
   - "Show me event details for [event-id]"

3. **Create Entity**
   - "Create a new user named 'john' with email john@test.com"
   - "Add a new profile for user [user-id]"

## Available Tools (37 Total)

**Auto-generated from schema.yaml** - Tools respect the `operations` field per entity.

### Entity Coverage

- **Account** (5 tools): list, get, create, update, delete
- **User** (4 tools): list, get, create, update (no delete)
- **Profile** (5 tools): list, get, create, update, delete
- **TagAffinity** (5 tools): list, get, create, update, delete
- **Event** (5 tools): list, get, create, update, delete
- **UserEvent** (5 tools): list, get, create, update, delete
- **Url** (5 tools): list, get, create, update, delete
- **Crawl** (2 tools): list, get, delete (read-only, no create/update)

### Tool Patterns

All tools follow these patterns:

**List Tools** (`list_{entity}s`):
- `page` (int, optional): Page number (default: 1)
- `pageSize` (int, optional): Items per page (default: 50, max: 100)
- `sort_by` (string, optional): Field to sort by, prefix with '-' for descending
- `filter_field` (string, optional): Field to filter on (enum of valid fields)
- `filter_value` (string, optional): Value to filter for

**Get Tools** (`get_{entity}`):
- `id` (string, required): Entity ID (ObjectId)

**Create Tools** (`create_{entity}`):
- Fields from schema.yaml (excludes autoGenerate/autoUpdate fields)
- Required fields marked in schema
- Includes all constraints (min/max length, enums, patterns)

**Update Tools** (`update_{entity}`):
- `id` (string, required): Entity ID to update
- All other fields optional
- Same constraints as create

**Delete Tools** (`delete_{entity}`):
- `id` (string, required): Entity ID to delete

### Example: User Tools

```python
# List users with filtering
list_users(
    page=1,
    pageSize=10,
    sort_by="-createdAt",
    filter_field="role",
    filter_value="admin"
)

# Get specific user
get_user(id="507f1f77bcf86cd799439011")

# Create new user (all required fields from schema)
create_user(
    username="john",
    email="john@test.com",
    password="password123",
    firstName="John",
    lastName="Doe",
    accountId="507f1f77bcf86cd799439011",
    isAccountOwner=True
)

# Update user (all fields optional except id)
update_user(
    id="507f1f77bcf86cd799439011",
    role="admin"
)
```

## Architecture

```
mcp_server.py                              # Entry point
└── app/mcp/
    ├── __init__.py                        # Package init
    ├── server.py                          # EventsMCPServer class
    ├── tools.py                           # Tool registry (uses registry.py)
    ├── registry.py                        # Generic CRUD tool generator
    └── schemas.py                         # Schema wrapper (uses gen_mcp.py)

../schema2rest/src/
└── generators/
    └── gen_mcp.py                         # MCP JSON Schema generator
```

### Key Design Decisions

1. **Metadata-Driven**: All tools auto-generated from schema.yaml
2. **Reuses Existing Infrastructure**: Leverages common.Schema from schema2rest
3. **Respects Operations**: Only generates allowed tools per entity (crud/rcu/rd)
4. **Type-Safe**: Full JSON Schema with constraints, enums, patterns
5. **Pattern Resolution**: Automatically resolves dictionary references

## Future Enhancements

Optional features that could be added:

- **Authentication**: MCP 'claude' user with ai_agent role
- **RBAC**: Field-level permissions and query limits
- **Audit Logging**: Track all MCP operations
- **Error Handling**: Structured error responses
- **Rate Limiting**: Prevent abuse
- **Batch Operations**: Create/update multiple entities at once

## Troubleshooting

### Server won't start

1. Check MongoDB is running
2. Verify mongo.json exists and is valid
3. Check logs for errors

### Tools not appearing in Claude Desktop

1. Verify configuration file location
2. Restart Claude Desktop
3. Check server logs

### Tool calls failing

1. Check database connectivity
2. Verify entity data exists (need Account before creating User)
3. Check tool handler logs

## Files Created/Modified

**MCP Server (events project):**
- `mcp_server.py` - Entry point script
- `app/mcp/__init__.py` - Package init
- `app/mcp/server.py` - MCP server implementation
- `app/mcp/tools.py` - Tool registry wrapper
- `app/mcp/registry.py` - Generic CRUD tool generator
- `app/mcp/schemas.py` - Schema generator wrapper
- `test_mcp.py` - Unit tests
- `claude_desktop_config.json` - Claude Desktop config
- `MCP_TESTING.md` - This file

**Schema Generator (schema2rest project):**
- `../schema2rest/src/generators/gen_mcp.py` - MCP JSON Schema generator

**Dependencies:**
- `requirements.txt` - Added `mcp==1.0.0`
