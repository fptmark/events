# MCP Server Environment Configuration

## Overview

The MCP server uses the **same configuration system** as the REST API server. You can switch between MongoDB, Elasticsearch, and SQLite using the `MCP_CONFIG` environment variable.

## Configuration Files

The MCP server loads database configuration from JSON files:

- `mongo.json` - MongoDB backend
- `es.json` - Elasticsearch backend
- `sqlite.json` - SQLite backend

These are the **same config files** used by the REST API server.

## How It Works

### Server Code (app/mcp/server.py:44)

```python
# Load config (default to mongo.json, can be overridden with env var)
config_path = os.getenv("MCP_CONFIG", "mongo.json")
logger.info(f"Loading config from: {config_path}")
Config.initialize(config_path)

# Initialize database
db_config = Config.get("database")
db_type = db_config.get("type", "mongodb")
db_uri = db_config.get("uri")
db_name = db_config.get("name")

logger.info(f"Connecting to {db_type} database...")
self.db = await DatabaseFactory.initialize(db_type, db_uri, db_name)
```

### Default Behavior

If `MCP_CONFIG` is not set, the server defaults to `mongo.json`.

## Switching Backends

### Option 1: Manual Testing

Run the MCP server manually with different backends:

```bash
# MongoDB (default)
python mcp_server.py

# MongoDB (explicit)
MCP_CONFIG=mongo.json python mcp_server.py

# SQLite
MCP_CONFIG=sqlite.json python mcp_server.py

# Elasticsearch
MCP_CONFIG=es.json python mcp_server.py
```

### Option 2: Claude Desktop Configuration

Edit your Claude Desktop config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

#### Single Backend Example

**MongoDB:**
```json
{
  "mcpServers": {
    "events-api": {
      "command": "python",
      "args": ["/Users/markmalamut/Projects/events/mcp_server.py"],
      "env": {
        "MCP_CONFIG": "/Users/markmalamut/Projects/events/mongo.json"
      }
    }
  }
}
```

**SQLite:**
```json
{
  "mcpServers": {
    "events-api": {
      "command": "python",
      "args": ["/Users/markmalamut/Projects/events/mcp_server.py"],
      "env": {
        "MCP_CONFIG": "/Users/markmalamut/Projects/events/sqlite.json"
      }
    }
  }
}
```

**Elasticsearch:**
```json
{
  "mcpServers": {
    "events-api": {
      "command": "python",
      "args": ["/Users/markmalamut/Projects/events/mcp_server.py"],
      "env": {
        "MCP_CONFIG": "/Users/markmalamut/Projects/events/es.json"
      }
    }
  }
}
```

#### Multiple Backends Simultaneously

You can run **all three backends at once** by giving each a unique name:

```json
{
  "mcpServers": {
    "events-mongo": {
      "command": "python",
      "args": ["/Users/markmalamut/Projects/events/mcp_server.py"],
      "env": {
        "MCP_CONFIG": "/Users/markmalamut/Projects/events/mongo.json"
      }
    },
    "events-sqlite": {
      "command": "python",
      "args": ["/Users/markmalamut/Projects/events/mcp_server.py"],
      "env": {
        "MCP_CONFIG": "/Users/markmalamut/Projects/events/sqlite.json"
      }
    },
    "events-es": {
      "command": "python",
      "args": ["/Users/markmalamut/Projects/events/mcp_server.py"],
      "env": {
        "MCP_CONFIG": "/Users/markmalamut/Projects/events/es.json"
      }
    }
  }
}
```

This creates **three separate MCP servers** in Claude Desktop:
- `events-mongo` - 37 tools using MongoDB
- `events-sqlite` - 37 tools using SQLite
- `events-es` - 37 tools using Elasticsearch

Claude will show you which server each tool belongs to, allowing you to compare backends or test migrations.

## Configuration File Format

Each JSON config file specifies the database connection:

### mongo.json
```json
{
  "database": {
    "type": "mongodb",
    "uri": "mongodb://localhost:27017",
    "name": "events"
  }
}
```

### sqlite.json
```json
{
  "database": {
    "type": "sqlite",
    "uri": "sqlite:///events.db",
    "name": "events"
  }
}
```

### es.json
```json
{
  "database": {
    "type": "elasticsearch",
    "uri": "http://localhost:9200",
    "name": "events"
  }
}
```

## Environment Variable Reference

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `MCP_CONFIG` | Path to config JSON file | `mongo.json` | `/path/to/sqlite.json` |

**Note**: The path can be absolute or relative to the project root.

## Verification

### Check Which Backend Is Running

When the MCP server starts, it logs the backend:

```
2025-10-23 20:00:00,000 - app.mcp.server - INFO - Loading config from: sqlite.json
2025-10-23 20:00:00,100 - app.mcp.server - INFO - Connecting to sqlite database...
2025-10-23 20:00:00,200 - app.mcp.server - INFO - Connected to sqlite successfully
```

### Test Backend Switching

1. Start with MongoDB:
   ```bash
   MCP_CONFIG=mongo.json python mcp_server.py
   # Should see: "Connecting to mongodb database..."
   ```

2. Stop server (Ctrl+C)

3. Switch to SQLite:
   ```bash
   MCP_CONFIG=sqlite.json python mcp_server.py
   # Should see: "Connecting to sqlite database..."
   ```

## Common Use Cases

### Development

Use SQLite for local development (no database server needed):
```bash
MCP_CONFIG=sqlite.json python mcp_server.py
```

### Production

Use MongoDB or Elasticsearch for production:
```bash
MCP_CONFIG=mongo.json python mcp_server.py
```

### Testing

Run multiple backends simultaneously in Claude Desktop to compare behavior:
- Create/update data in MongoDB
- Verify same data appears in Elasticsearch (if synced)
- Check SQLite has local test data

### CI/CD

Use environment variable in test scripts:
```bash
export MCP_CONFIG=sqlite.json
python mcp_server.py &
# Run tests
kill %1
```

## Troubleshooting

### MCP Server Won't Start

**Check 1: Database is running**
```bash
# MongoDB
mongosh --eval "db.version()"

# Elasticsearch
curl http://localhost:9200

# SQLite (no server needed)
ls -l events.db
```

**Check 2: Config file exists**
```bash
# Verify config file path
ls -l mongo.json sqlite.json es.json
```

**Check 3: Environment variable is set correctly**
```bash
echo $MCP_CONFIG
# Should show: mongo.json, sqlite.json, or es.json
```

### Wrong Backend Loading

**Problem**: MCP server uses MongoDB when you specified SQLite

**Solution**: Check environment variable in Claude Desktop config:
```json
{
  "env": {
    "MCP_CONFIG": "/full/path/to/sqlite.json"  // Use absolute path
  }
}
```

### Multiple Servers Conflict

**Problem**: Running multiple MCP servers with same name

**Solution**: Use unique names in Claude Desktop config:
```json
{
  "mcpServers": {
    "events-mongo": { ... },    // Good: unique name
    "events-sqlite": { ... },   // Good: unique name
    "events-api": { ... }       // Bad: conflicts if used twice
  }
}
```

## Architecture Notes

The MCP server uses the **exact same database layer** as the REST API:

```
MCP Tools
    ↓
ModelService (User.get_all, User.create, etc.)
    ↓
DatabaseFactory
    ↓
Database Driver (MongoDB / Elasticsearch / SQLite)
```

This means:
- **Same data models** - Pydantic validation
- **Same metadata** - Field definitions from schema.yaml
- **Same operations** - CRUD operations identical to REST API
- **Same backends** - MongoDB, Elasticsearch, SQLite

**The only difference is the interface**: REST uses HTTP, MCP uses stdio.

## Related Files

- `app/mcp/server.py` - MCP server initialization and config loading
- `app/config.py` - Config class (shared with REST API)
- `app/db/__init__.py` - DatabaseFactory (shared with REST API)
- `claude_desktop_config.json` - Example Claude Desktop config
- `mongo.json` / `sqlite.json` / `es.json` - Database config files
