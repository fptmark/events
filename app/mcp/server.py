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


class EventsMCPServer:
    """MCP server wrapping Events API"""

    def __init__(self):
        self.server = Server("events-api")
        self.db = None
        self.mcp_user = None
        self.auth_context = None
        self._initialized = False

    async def initialize(self):
        """Initialize database and services"""
        if self._initialized:
            return

        logger.info("Initializing MCP server...")

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
        logger.info(f"Connected to {db_type} successfully")

        # Initialize metadata service
        entities = [
            "Account", "User", "Profile", "TagAffinity",
            "Event", "UserEvent", "Url", "Crawl"
        ]
        MetadataService.initialize(entities)
        ModelService.initialize(entities)
        logger.info(f"Initialized {len(entities)} entities")

        # TODO: Authenticate as MCP service user
        # Will implement in Phase 2 Day 4
        logger.info("MCP authentication (will be implemented in Phase 2)")

        self._initialized = True
        logger.info("MCP server initialized successfully")

    async def shutdown(self):
        """Cleanup on server shutdown"""
        logger.info("Shutting down MCP server...")
        if self.db:
            await DatabaseFactory.close()
            logger.info("Database connection closed")

    def register_tools(self):
        """Register all MCP tools"""
        # Import tools registry
        from .tools import get_all_tools

        tools = get_all_tools()
        logger.info(f"Registering {len(tools)} MCP tools...")

        for tool in tools:
            self.server.add_tool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["input_schema"],
                handler=tool["handler"]
            )

        logger.info(f"Registered {len(tools)} tools successfully")

    async def run(self):
        """Run the MCP server"""
        await self.initialize()
        self.register_tools()

        logger.info("Starting MCP server (stdio transport)...")

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
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.exception(f"Server error: {e}")
        raise
    finally:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
