"""
Router factory for reading schema and managing model imports with caching.

This module handles schema reading, model imports, and caching to optimize
the dynamic router creation process and avoid expensive importlib operations.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Type, List, Protocol
from pydantic import BaseModel


class EntityModelProtocol(Protocol):
    """Protocol for entity model classes with required methods and attributes."""
    _metadata: Dict[str, Any]
    
    @classmethod
    async def get_all(cls) -> Dict[str, Any]: ...
    
    @classmethod
    async def get_list(cls, list_params) -> Dict[str, Any]: ...
    
    @classmethod
    async def get(cls, entity_id: str): ...
    
    async def save(self, entity_id: str = '') -> tuple: ...
    
    @classmethod
    async def delete(cls, entity_id: str) -> tuple[bool, list]: ...
    
    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> 'EntityModelProtocol': ...
import importlib

logger = logging.getLogger(__name__)


def get_entity_names(schema_path: Path) -> List[str]:
    """
    Get entity names directly from schema.yaml.
    
    Returns:
        List of entity names (e.g., ['User', 'Account', 'Event'])
    """
    
    try:
        with open(schema_path, 'r') as f:
            schema = yaml.safe_load(f)
        
        entity_names = [ 
            name for name, attrs in schema.get('_entities', {}).items()
            if not attrs.get('abstract', False) 
        ]
        logger.info(f"Found {len(entity_names)} entities in schema.yaml: {entity_names}")
        return entity_names
        
    except FileNotFoundError:
        logger.error(f"schema.yaml not found at {schema_path}")
        return []
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in schema.yaml: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to read schema.yaml: {e}")
        return []


class ModelImportCache:
    """Centralized cache for all model class imports to avoid repeated importlib operations."""
    
    # Cache for imported model classes to avoid repeated imports
    _model_class_cache: Dict[str, Type[EntityModelProtocol]] = {}
    _create_class_cache: Dict[str, Type[BaseModel]] = {}
    _update_class_cache: Dict[str, Type[BaseModel]] = {}
    
    @classmethod
    def get_model_class(cls, entity_name: str) -> Type[EntityModelProtocol]:
        """Dynamically import the main model class with caching."""
        # Check cache first
        if entity_name in cls._model_class_cache:
            return cls._model_class_cache[entity_name]
            
        try:
            module_name = f"app.models.{entity_name.lower()}_model"
            module = importlib.import_module(module_name)
            model_class = getattr(module, entity_name)
            
            # Cache the result
            cls._model_class_cache[entity_name] = model_class
            return model_class
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import model class {entity_name}: {e}")
            raise ImportError(f"Could not import model class {entity_name}")
    
    @classmethod
    def get_create_class(cls, entity_name: str) -> Type[BaseModel]:
        """Dynamically import the Create model class with caching."""
        # Check cache first
        if entity_name in cls._create_class_cache:
            return cls._create_class_cache[entity_name]
            
        try:
            module_name = f"app.models.{entity_name.lower()}_model"
            module = importlib.import_module(module_name)
            create_class = getattr(module, f"{entity_name}Create")
            
            # Cache the result
            cls._create_class_cache[entity_name] = create_class
            return create_class
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import create class {entity_name}Create: {e}")
            raise ImportError(f"Could not import create class {entity_name}Create")
    
    @classmethod
    def get_update_class(cls, entity_name: str) -> Type[BaseModel]:
        """Dynamically import the Update model class with caching."""
        # Check cache first
        if entity_name in cls._update_class_cache:
            return cls._update_class_cache[entity_name]
            
        try:
            module_name = f"app.models.{entity_name.lower()}_model"
            module = importlib.import_module(module_name)
            update_class = getattr(module, f"{entity_name}Update")
            
            # Cache the result
            cls._update_class_cache[entity_name] = update_class
            return update_class
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import update class {entity_name}Update: {e}")
            raise ImportError(f"Could not import update class {entity_name}Update")
    
    @classmethod
    def clear_cache(cls):
        """Clear all caches - useful for testing or development."""
        cls._model_class_cache.clear()
        cls._create_class_cache.clear()
        cls._update_class_cache.clear()
        logger.info("Model import caches cleared")