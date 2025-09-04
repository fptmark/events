"""
Router factory for reading schema and managing model imports with caching.

This module handles schema reading, model imports, and caching to optimize
the dynamic router creation process and avoid expensive importlib operations.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Type, List, Protocol
from pydantic import BaseModel


class EntityModelProtocol(Protocol):
    """Protocol for entity model classes with required methods and attributes."""
    _metadata: Dict[str, Any]
    
    @classmethod
    async def get_all(cls, sort: List[tuple], filter: Dict[str, Any] | None, page: int, pageSize: int, view_spec: Dict[str, Any] | None) -> Tuple[List[Dict[str, Any]], int]: ...
    
    @classmethod
    async def get(cls, entity_id: str, view_spec: Dict[str, Any] | None) -> Tuple[Dict[str, Any], int]: ...
    
    @classmethod
    async def create(cls, data: Dict[str, Any], validate: bool = True) -> Tuple[Dict[str, Any], int]: ...
    
    @classmethod
    async def update(cls, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]: ...
    
    @classmethod
    async def delete(cls, entity_id: str) -> Tuple[Dict[str, Any], int]: ...
    
    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> 'EntityModelProtocol': ...
import importlib

logger = logging.getLogger(__name__)


# def get_entity_names(schema_path: Path) -> List[str]:
#     """
#     Get entity names directly from schema.yaml.
    
#     Returns:
#         List of entity names (e.g., ['User', 'Account', 'Event'])
#     """
    
#     try:
#         with open(schema_path, 'r') as f:
#             schema = yaml.safe_load(f)
        
#         entity_names = [ 
#             name for name, attrs in schema.get('_entities', {}).items()
#             if not attrs.get('abstract', False) 
#         ]
#         logger.info(f"Found {len(entity_names)} entities in schema.yaml: {entity_names}")
#         return entity_names
        
#     except FileNotFoundError:
#         logger.error(f"schema.yaml not found at {schema_path}")
#         return []
#     except yaml.YAMLError as e:
#         logger.error(f"Invalid YAML in schema.yaml: {e}")
#         return []
#     except Exception as e:
#         logger.error(f"Failed to read schema.yaml: {e}")
#         return []


