#!/usr/bin/env python3
"""
MCP server entry point.

Usage:
    python mcp_server.py

Environment variables:
    MCP_CONFIG - Path to config file (default: mongo.json)
    MCP_USER - MCP service username (default: claude_mcp)
    MCP_PASSWORD - MCP service password (required for auth)
"""
import asyncio
from app.mcp.server import main

if __name__ == "__main__":
    asyncio.run(main())
