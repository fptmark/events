"""
MCP client wrapper for testing.
Handles stdio communication with MCP server.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class MCPConfig:
    """MCP server configuration"""
    server_script: str  # Path to mcp_server.py
    config_file: str    # Path to mongo.json/sqlite.json/es.json
    python_cmd: str = "python"


class MCPClient:
    """
    MCP client for testing.
    Launches MCP server as subprocess and communicates via stdio.
    """

    def __init__(self, config: MCPConfig, verbose: bool = False):
        """
        Initialize MCP client.

        Args:
            config: MCP server configuration
            verbose: Enable verbose logging
        """
        self.config = config
        self.verbose = verbose
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 0
        self._initialized = False

    async def start(self) -> None:
        """Start the MCP server process"""
        if self.process:
            return  # Already started

        if self.verbose:
            print(f"🚀 Starting MCP server: {self.config.server_script}")
            print(f"   Config: {self.config.config_file}")

        # Start MCP server process
        env = {
            "MCP_CONFIG": self.config.config_file
        }

        self.process = await asyncio.create_subprocess_exec(
            self.config.python_cmd,
            self.config.server_script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        # Wait for initialization
        await self._initialize()

        if self.verbose:
            print("✅ MCP server started successfully")

    async def _initialize(self) -> None:
        """Initialize MCP session"""
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp-validate",
                    "version": "1.0.0"
                }
            }
        }

        response = await self._send_request(init_request)

        if "error" in response:
            raise RuntimeError(f"MCP initialization failed: {response['error']}")

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

        await self._send_notification(initialized_notification)

        self._initialized = True

    async def stop(self) -> None:
        """Stop the MCP server process"""
        if not self.process:
            return

        if self.verbose:
            print("🛑 Stopping MCP server...")

        # Send shutdown request
        try:
            await self.call_method("shutdown")
        except Exception as e:
            logger.warning(f"Shutdown request failed: {e}")

        # Terminate process
        self.process.terminate()
        await self.process.wait()

        self.process = None
        self._initialized = False

        if self.verbose:
            print("✅ MCP server stopped")

    def _next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send JSON-RPC request and wait for response.

        Args:
            request: JSON-RPC request

        Returns:
            JSON-RPC response
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not started")

        # Send request
        request_str = json.dumps(request) + "\n"
        self.process.stdin.write(request_str.encode())
        await self.process.stdin.drain()

        if self.verbose:
            logger.debug(f"→ {request}")

        # Read response
        if not self.process.stdout:
            raise RuntimeError("No stdout available")

        response_bytes = await self.process.stdout.readline()
        response_str = response_bytes.decode().strip()

        if not response_str:
            raise RuntimeError("Empty response from MCP server")

        response = json.loads(response_str)

        if self.verbose:
            logger.debug(f"← {response}")

        return response

    async def _send_notification(self, notification: Dict[str, Any]) -> None:
        """
        Send JSON-RPC notification (no response expected).

        Args:
            notification: JSON-RPC notification
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server not started")

        notification_str = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_str.encode())
        await self.process.stdin.drain()

        if self.verbose:
            logger.debug(f"→ {notification}")

    async def call_method(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call MCP method.

        Args:
            method: Method name
            params: Method parameters

        Returns:
            Method result

        Raises:
            RuntimeError: If method call fails
        """
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {}
        }

        response = await self._send_request(request)

        if "error" in response:
            error = response["error"]
            raise RuntimeError(f"MCP error: {error.get('message', error)}")

        return response.get("result")

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call MCP tool.

        Args:
            tool_name: Tool name (e.g., "create_user", "get_account")
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            RuntimeError: If tool call fails
        """
        if not self._initialized:
            raise RuntimeError("MCP client not initialized")

        params = {
            "name": tool_name,
            "arguments": arguments or {}
        }

        result = await self.call_method("tools/call", params)

        # MCP tools/call returns {content: [...]}
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if content and len(content) > 0:
                # First content item should have the result
                first_item = content[0]
                if isinstance(first_item, dict) and "text" in first_item:
                    # Parse JSON result from text
                    return json.loads(first_item["text"])
                return first_item

        return result

    async def list_tools(self) -> list:
        """
        List available MCP tools.

        Returns:
            List of tool definitions
        """
        result = await self.call_method("tools/list")
        return result.get("tools", [])

    async def clean_database(self) -> None:
        """Clean database via /api/db/init/confirmed endpoint"""
        # Note: MCP tools don't expose admin endpoints directly
        # We need to call the REST API for this
        import aiohttp

        # Determine server URL from config
        # TODO: Read from config file
        server_url = "http://localhost:5500"

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{server_url}/api/db/init/confirmed") as resp:
                if resp.status not in [200, 201]:
                    text = await resp.text()
                    raise RuntimeError(f"Database init failed: {resp.status} {text}")

        if self.verbose:
            print("✅ Database cleaned via /api/db/init/confirmed")

    async def get_database_type(self) -> str:
        """Get database type from /api/db/report endpoint"""
        import aiohttp

        server_url = "http://localhost:5500"

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server_url}/api/db/report") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("database", "unknown")

        return "unknown"
