#!/usr/bin/env python3
"""
MCP Validator - Test runner for MCP server
"""
import asyncio
from mcp_validate.runner import main

if __name__ == "__main__":
    asyncio.run(main())
