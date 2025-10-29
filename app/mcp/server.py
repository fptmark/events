"""
MCP server for Events API.
Exposes database entities and operations as MCP tools via HTTP REST API.
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to Python path (so imports work without PYTHONPATH)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.stdio import stdio_server

from app.config import Config
from app.mcp.registry_http import HTTPToolRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("events-api")

# Global state
_registry = None
_initialized = False


async def initialize_registry():
    """Initialize HTTP tool registry from REST API metadata"""
    global _registry, _initialized
    if _initialized:
        return

    logger.info("Initializing HTTP tool registry...")

    # Load config
    config_path = os.getenv("MCP_CONFIG", "mongo.json")
    Config.initialize(config_path)

    # Create and initialize HTTP registry
    _registry = HTTPToolRegistry()
    await _registry.initialize()

    _initialized = True
    logger.info(f"Registry initialized with {len(_registry.get_tools())} tools")


@server.list_tools()
async def handle_list_tools():
    """List available tools"""
    await initialize_registry()

    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": tool["inputSchema"]
        }
        for tool in _registry.get_tools()
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """Handle tool calls"""
    await initialize_registry()

    # Find the tool
    tools = _registry.get_tools()
    tool = next((t for t in tools if t["name"] == name), None)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")

    # Call the handler
    result = await tool["handler"](**arguments)

    # Format result as text content (MCP SDK requirement)
    return [{"type": "text", "text": json.dumps(result, indent=2)}]


async def main():
    """Entry point"""
    try:
        logger.info("Starting HTTP-based MCP server...")
        logger.info("NOTE: REST API server must be running at http://localhost:5500")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except KeyboardInterrupt:
        logger.info("Shutdown")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
