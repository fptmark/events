"""
MCP server for Events API.
Exposes database entities and operations as MCP tools.
"""
import asyncio
import logging
import os
from typing import Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server

from app.config import Config
from app.db import DatabaseFactory
from app.services.metadata import MetadataService
from app.services.model import ModelService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("events-api")

# Global state
_db_initialized = False
_tools = []


async def initialize_database():
    """Initialize database and services"""
    global _db_initialized
    if _db_initialized:
        return

    logger.info("Initializing database...")

    # Load config
    config_path = os.getenv("MCP_CONFIG", "mongo.json")
    Config.initialize(config_path)

    # Initialize database
    db_type = Config.get("database")
    db_uri = Config.get("db_uri")
    db_name = Config.get("db_name")

    await DatabaseFactory.initialize(db_type, db_uri, db_name)

    # Initialize metadata
    entities = ["Account", "User", "Profile", "TagAffinity", "Event", "UserEvent", "Url", "Crawl"]
    MetadataService.initialize(entities)
    ModelService.initialize(entities)

    _db_initialized = True
    logger.info("Database initialized")


# Load tool registry
from app.mcp.tools import get_all_tools
_tools = get_all_tools()
logger.info(f"Loaded {len(_tools)} tools from registry")


@server.list_tools()
async def handle_list_tools():
    """List available tools"""
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": tool["input_schema"]
        }
        for tool in _tools
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle tool calls"""
    await initialize_database()

    # Find the tool
    tool = next((t for t in _tools if t["name"] == name), None)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")

    # Call the handler
    result = await tool["handler"](**arguments)
    return result


async def main():
    """Entry point"""
    try:
        logger.info("Starting MCP server...")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Shutdown")
    finally:
        if _db_initialized:
            await DatabaseFactory.close()


if __name__ == "__main__":
    asyncio.run(main())
