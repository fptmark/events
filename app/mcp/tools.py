"""
MCP tools registry and handlers.
Uses generic registry that auto-generates tools from schema.yaml.
"""
from typing import Any, Dict, List
import logging

from .registry import ToolRegistry

logger = logging.getLogger(__name__)


def get_all_tools() -> List[Dict[str, Any]]:
    """
    Get all registered MCP tools.
    Auto-generates tools for all entities from schema.yaml.

    Returns list of tool definitions with:
    - name: Tool name
    - description: Tool description
    - input_schema: JSON Schema for parameters
    - handler: Async function to call
    """
    logger.info("Building MCP tool registry from schema.yaml...")

    # Create registry and auto-register all entities
    registry = ToolRegistry()
    registry.register_all_entities()

    tools = registry.get_all_tools()
    logger.info(f"Generated {len(tools)} tools from schema.yaml")

    return tools
