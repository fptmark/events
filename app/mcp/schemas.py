"""
MCP schema wrapper.
Uses gen_mcp.py from schema2rest for schema generation.
"""
import sys
from pathlib import Path

# Add schema2rest to path
schema2rest_path = Path(__file__).resolve().parent.parent.parent.parent / "schema2rest" / "src"
if str(schema2rest_path) not in sys.path:
    sys.path.insert(0, str(schema2rest_path))

from generators.gen_mcp import MCPSchemaGenerator
from common.schema import Schema


# Create singleton instance
_generator = None


def get_generator(schema_path: str = "schema.yaml") -> MCPSchemaGenerator:
    """
    Get MCP schema generator instance.

    Args:
        schema_path: Path to schema.yaml

    Returns:
        MCPSchemaGenerator instance
    """
    global _generator
    if _generator is None:
        schema = Schema(schema_path)
        _generator = MCPSchemaGenerator(schema)
    return _generator
