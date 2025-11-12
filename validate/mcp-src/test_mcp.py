#!/usr/bin/env python3
"""
MCP Validator - Tests MCP server tooling for format compliance.

Tests:
1. Tool registration and schema format
2. Handler response format (MCP SDK compatibility)
3. Server API response format (shallow check for structure changes)
4. Error response format

Fails hard with clear messages if format doesn't match expectations.
"""
import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import Config
from app.mcp.registry_http import HTTPToolRegistry


class MCPValidator:
    """Validates MCP server tooling and response formats"""

    def __init__(self):
        self.registry: HTTPToolRegistry = None
        self.failures: List[str] = []
        self.passes: int = 0

    async def initialize(self):
        """Initialize the MCP registry"""
        print("Initializing MCP registry...")

        # Load config
        config_path = os.getenv("MCP_CONFIG", str(project_root / "mongo.json"))
        Config.initialize(config_path)

        # Create and initialize HTTP registry
        self.registry = HTTPToolRegistry()
        await self.registry.initialize()

        print(f"Registry initialized with {len(self.registry.get_tools())} tools\n")

    def fail(self, message: str):
        """Record a failure"""
        self.failures.append(f"❌ FAIL: {message}")
        print(f"  ❌ {message}")

    def pass_test(self, message: str):
        """Record a pass"""
        self.passes += 1
        print(f"  ✓ {message}")

    def validate_tool_schema(self, tool: Dict[str, Any]) -> bool:
        """Validate tool has correct MCP schema format"""
        test_name = f"Tool schema: {tool['name']}"

        # Check required fields
        if "name" not in tool:
            self.fail(f"{test_name} - missing 'name' field")
            return False

        if "description" not in tool:
            self.fail(f"{test_name} - missing 'description' field")
            return False

        if "inputSchema" not in tool:
            self.fail(f"{test_name} - missing 'inputSchema' field")
            return False

        if "handler" not in tool:
            self.fail(f"{test_name} - missing 'handler' field")
            return False

        # Validate inputSchema structure
        schema = tool["inputSchema"]
        if schema.get("type") != "object":
            self.fail(f"{test_name} - inputSchema.type must be 'object'")
            return False

        if "properties" not in schema:
            self.fail(f"{test_name} - inputSchema missing 'properties'")
            return False

        self.pass_test(test_name)
        return True

    async def validate_handler_response_format(self, tool: Dict[str, Any]) -> bool:
        """Validate handler returns dict that can be wrapped in MCP format"""
        tool_name = tool["name"]
        test_name = f"Handler returns dict: {tool_name}"

        try:
            # Get test arguments based on tool type
            args = self._get_test_args(tool_name, tool["inputSchema"])

            # Call handler - should return dict
            result = await tool["handler"](**args)

            # Registry handlers should return dicts (or error dicts)
            if not isinstance(result, dict):
                self.fail(f"{test_name} - handler must return dict, got {type(result).__name__}")
                return False

            self.pass_test(test_name)
            return True

        except Exception as e:
            self.fail(f"{test_name} - handler raised exception: {str(e)}")
            return False

    async def validate_mcp_wrapped_format(self, tool: Dict[str, Any]) -> bool:
        """Validate that handler result can be wrapped in MCP format correctly"""
        tool_name = tool["name"]
        test_name = f"MCP format wrapping: {tool_name}"

        try:
            # Get test arguments
            args = self._get_test_args(tool_name, tool["inputSchema"])

            # Call handler and get raw result
            result = await tool["handler"](**args)

            # Simulate server.py's handle_call_tool wrapper
            mcp_response = [{"type": "text", "text": json.dumps(result, indent=2)}]

            # Validate MCP format
            if not isinstance(mcp_response, list):
                self.fail(f"{test_name} - MCP response must be a list")
                return False

            if len(mcp_response) == 0:
                self.fail(f"{test_name} - MCP response list is empty")
                return False

            content = mcp_response[0]
            if not isinstance(content, dict):
                self.fail(f"{test_name} - content must be dict")
                return False

            if content.get("type") != "text":
                self.fail(f"{test_name} - content.type must be 'text'")
                return False

            if "text" not in content:
                self.fail(f"{test_name} - content missing 'text' field")
                return False

            if not isinstance(content["text"], str):
                self.fail(f"{test_name} - content.text must be string")
                return False

            # Verify the JSON is valid
            json.loads(content["text"])

            self.pass_test(test_name)
            return True

        except json.JSONDecodeError as e:
            self.fail(f"{test_name} - wrapped JSON is invalid: {str(e)}")
            return False
        except Exception as e:
            self.fail(f"{test_name} - error: {str(e)}")
            return False

    async def validate_server_response_structure(self, tool: Dict[str, Any]) -> bool:
        """Shallow check that server API response has expected structure"""
        tool_name = tool["name"]
        test_name = f"Server response structure: {tool_name}"

        try:
            # Get test arguments
            args = self._get_test_args(tool_name, tool["inputSchema"])

            # Call handler - returns dict directly
            server_data = await tool["handler"](**args)

            # Check for error response format
            if "error" in server_data:
                # Error response format
                if "status" not in server_data:
                    self.fail(f"{test_name} - error response missing 'status' field")
                    return False
                self.pass_test(f"{test_name} (error response)")
                return True

            # Check success response format for list operations
            if tool_name.startswith("list_"):
                # List response: {entity_plural: [], total: N, page: N, pageSize: N}
                entity = tool_name.replace("list_", "")
                plural_key = f"{entity}s"

                if plural_key not in server_data:
                    self.fail(f"{test_name} - missing '{plural_key}' field")
                    return False

                if "total" not in server_data:
                    self.fail(f"{test_name} - missing 'total' field")
                    return False

                if "page" not in server_data:
                    self.fail(f"{test_name} - missing 'page' field")
                    return False

                if "pageSize" not in server_data:
                    self.fail(f"{test_name} - missing 'pageSize' field")
                    return False

            elif tool_name.startswith("get_"):
                # Get response: {field1: value1, field2: value2, ...}
                if not isinstance(server_data, dict):
                    self.fail(f"{test_name} - response must be dict")
                    return False

            elif tool_name.startswith("create_") or tool_name.startswith("update_"):
                # Create/Update response: {field1: value1, field2: value2, ...}
                if not isinstance(server_data, dict):
                    self.fail(f"{test_name} - response must be dict")
                    return False

            elif tool_name.startswith("delete_"):
                # Delete response: {success: true, id: ...}
                if "success" not in server_data:
                    self.fail(f"{test_name} - missing 'success' field")
                    return False

                if "id" not in server_data:
                    self.fail(f"{test_name} - missing 'id' field")
                    return False

            self.pass_test(test_name)
            return True

        except Exception as e:
            self.fail(f"{test_name} - validation error: {str(e)}")
            return False

    def _get_test_args(self, tool_name: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test arguments for a tool"""
        # Use minimal valid arguments for testing

        if tool_name.startswith("list_"):
            return {"page": 1, "pageSize": 1}

        elif tool_name.startswith("get_"):
            # Check if schema actually requires id parameter
            if "id" in schema.get("properties", {}):
                return {"id": "test_001"}
            else:
                return {}  # No parameters (e.g., get_session)

        elif tool_name.startswith("delete_"):
            # Use a non-existent ID to avoid actually deleting
            return {"id": "nonexistent_999"}

        elif tool_name.startswith("create_"):
            # Skip create tests - don't want to create test data
            raise Exception("Skipping create test")

        elif tool_name.startswith("update_"):
            # Skip update tests - don't want to modify test data
            raise Exception("Skipping update test")

        return {}

    async def run_tests(self):
        """Run all MCP validation tests"""
        print("=" * 60)
        print("MCP VALIDATOR - Testing MCP Server Tooling")
        print("=" * 60)
        print()

        await self.initialize()

        tools = self.registry.get_tools()

        # Test 1: Tool schema validation
        print("Test 1: Tool Schema Validation")
        print("-" * 60)
        for tool in tools:
            self.validate_tool_schema(tool)
        print()

        # Test 2: Handler returns dict (not MCP-wrapped)
        print("Test 2: Handler Returns Dict (Registry Level)")
        print("-" * 60)
        for tool in tools:
            # Only test list and get operations (safe, non-mutating)
            if tool["name"].startswith("list_") or tool["name"].startswith("get_"):
                await self.validate_handler_response_format(tool)
        print()

        # Test 3: MCP format wrapping (simulates server.py wrapper)
        print("Test 3: MCP Format Wrapping (SDK Compatibility)")
        print("-" * 60)
        for tool in tools:
            # Only test list and get operations
            if tool["name"].startswith("list_") or tool["name"].startswith("get_"):
                await self.validate_mcp_wrapped_format(tool)
        print()

        # Test 4: Server response structure validation
        print("Test 4: Server API Response Structure (Shallow Check)")
        print("-" * 60)
        for tool in tools:
            # Only test list and get operations
            if tool["name"].startswith("list_") or tool["name"].startswith("get_"):
                await self.validate_server_response_structure(tool)
        print()

        # Print summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Passed: {self.passes}")
        print(f"Failed: {len(self.failures)}")
        print()

        if self.failures:
            print("FAILURES:")
            for failure in self.failures:
                print(failure)
            print()
            return False
        else:
            print("✓ All tests passed!")
            print()
            return True


async def main():
    """Entry point"""
    validator = MCPValidator()
    success = await validator.run_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
