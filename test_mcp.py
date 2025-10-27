#!/usr/bin/env python3
"""
Test script for MCP server.
Verifies server initialization and tool registration.
"""
import asyncio
import json
from app.mcp.tools import get_all_tools


async def test_tools():
    """Test tool registry"""
    print("Testing MCP tools registry...")
    print()

    tools = get_all_tools()
    print(f"✓ Found {len(tools)} tools")
    print()

    # Group tools by entity
    tools_by_entity = {}
    for tool in tools:
        # Extract entity from tool name (e.g., list_users -> User)
        parts = tool['name'].split('_')
        if len(parts) >= 2:
            action = parts[0]
            entity = parts[1].rstrip('s').capitalize()
            if entity not in tools_by_entity:
                tools_by_entity[entity] = []
            tools_by_entity[entity].append(tool['name'])

    print("Tools by entity:")
    for entity, tool_names in sorted(tools_by_entity.items()):
        print(f"  {entity}: {', '.join(tool_names)}")
    print()

    # Show details for first 3 tools
    print("Sample tool details (first 3):")
    print()
    for tool in tools[:3]:
        print(f"Tool: {tool['name']}")
        print(f"  Description: {tool['description']}")
        print(f"  Handler: {tool['handler'].__name__}")

        # Show input schema
        schema = tool['input_schema']
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        print(f"  Parameters: {len(properties)} total")
        # Show first 3 params
        for i, (param_name, param_spec) in enumerate(list(properties.items())[:3]):
            is_required = param_name in required
            param_type = param_spec.get('type', 'unknown')
            req_marker = " (required)" if is_required else ""
            print(f"    - {param_name}: {param_type}{req_marker}")
        if len(properties) > 3:
            print(f"    ... and {len(properties) - 3} more")

        print()


async def test_server_import():
    """Test server imports correctly"""
    print("Testing MCP server imports...")

    try:
        from app.mcp.server import EventsMCPServer
        print("✓ EventsMCPServer imports successfully")

        server = EventsMCPServer()
        print("✓ EventsMCPServer instantiates successfully")
        print(f"  Server name: events-api")
        print()

    except Exception as e:
        print(f"✗ Import failed: {e}")
        raise


async def main():
    """Run all tests"""
    print("=" * 60)
    print("MCP Server Test Suite")
    print("=" * 60)
    print()

    try:
        await test_server_import()
        await test_tools()

        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print()
        print("To test with Claude Desktop:")
        print("  1. Copy claude_desktop_config.json contents to:")
        print("     ~/Library/Application Support/Claude/claude_desktop_config.json")
        print()
        print("  2. Restart Claude Desktop")
        print()
        print("  3. Look for 'events-api' in the MCP tools menu")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Tests failed: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    asyncio.run(main())
