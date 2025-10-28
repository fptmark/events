#!/usr/bin/env python3
"""
Simple MCP server that wraps REST API endpoints.
Only makes HTTP calls - does NOT import any application code.
"""
import asyncio
import logging
import os
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config to get REST API URL
config_path = os.getenv("MCP_CONFIG", "mongo.json")
with open(config_path, "r") as f:
    config = json.load(f)

host = config.get("host", "localhost")
port = config.get("server_port", 5500)
API_BASE = f"http://{host}:{port}/api"

logger.info(f"REST API endpoint: {API_BASE}")

# Create MCP server
server = Server("events-api")


@server.list_tools()
async def handle_list_tools():
    """List available tools"""
    return [
        {
            "name": "list_users",
            "description": "List all users with pagination",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "page": {"type": "number", "default": 1},
                    "pageSize": {"type": "number", "default": 50}
                }
            }
        },
        {
            "name": "get_user",
            "description": "Get a single user by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "User ID"}
                },
                "required": ["id"]
            }
        }
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle tool calls by making REST API requests"""
    async with httpx.AsyncClient() as client:
        if name == "list_users":
            page = arguments.get("page", 1)
            page_size = arguments.get("pageSize", 50)
            response = await client.get(
                f"{API_BASE}/user",
                params={"page": page, "pageSize": page_size}
            )
            response.raise_for_status()
            data = response.json()

            # Format response for MCP
            return [{"type": "text", "text": json.dumps(data, indent=2)}]

        elif name == "get_user":
            user_id = arguments["id"]
            response = await client.get(f"{API_BASE}/user/{user_id}")
            response.raise_for_status()
            data = response.json()

            # Format response for MCP
            return [{"type": "text", "text": json.dumps(data, indent=2)}]

        else:
            raise ValueError(f"Unknown tool: {name}")


async def main():
    """Entry point"""
    logger.info(f"Starting MCP REST server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
