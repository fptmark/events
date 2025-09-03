"""
ModelService for managing entity model classes.
Initialized at startup to avoid dynamic import issues.
"""

from typing import Dict, Type, Any
import importlib
import logging

logger = logging.getLogger(__name__)


class ModelService:
    """Static service for accessing pre-loaded entity model classes."""
    
    _models: Dict[str, Type[Any]] = {}
    _create_models: Dict[str, Type[Any]] = {}
    _update_models: Dict[str, Type[Any]] = {}
    
    @classmethod
    def initialize(cls, entity_names: list[str]) -> None:
        """Initialize ModelService with all entity model classes.
        
        Args:
            entity_names: List of entity names (e.g., ["User", "Account", "Profile"])
        """
        logger.info(f"Initializing ModelService with {len(entity_names)} entities...")
        
        for entity_name in entity_names:
            try:
                # Import model classes (e.g., User, UserCreate, UserUpdate from app.models.user_model)
                module_name = f"app.models.{entity_name.lower()}_model"
                module = importlib.import_module(module_name)
                
                # Main model class
                model_class = getattr(module, entity_name)
                cls._models[entity_name] = model_class
                
                # Create class (e.g., UserCreate)
                try:
                    create_class = getattr(module, f"{entity_name}Create")
                    cls._create_models[entity_name] = create_class
                except AttributeError:
                    logger.warning(f"No {entity_name}Create class found")
                
                # Update class (e.g., UserUpdate)
                try:
                    update_class = getattr(module, f"{entity_name}Update")
                    cls._update_models[entity_name] = update_class
                except AttributeError:
                    logger.warning(f"No {entity_name}Update class found")
                
                logger.debug(f"Loaded model classes for: {entity_name}")
                
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to load model {entity_name}: {e}")
                raise RuntimeError(f"Failed to load required model {entity_name}: {e}")
        
        logger.info(f"ModelService initialized with {len(cls._models)} model classes")
    
    @classmethod
    def get_model_class(cls, entity_name: str) -> Type[Any] | None:
        """Get pre-loaded model class by entity name.
        
        Args:
            entity_name: Entity name (e.g., "User", "Account")
            
        Returns:
            Model class or None if not found
            
        Raises:
            RuntimeError: Only if ModelService not initialized
        """
        # Case-insensitive lookup
        for name, model_class in cls._models.items():
            if name.lower() == entity_name.lower():
                return model_class
        return None
    
    @classmethod
    def get_create_class(cls, entity_name: str) -> Type[Any] | None:
        """Get pre-loaded create class by entity name.
        
        Args:
            entity_name: Entity name (e.g., "User" returns UserCreate)
            
        Returns:
            Create class or None if not found
            
        Raises:
            RuntimeError: Only if ModelService not initialized
        """
        # Case-insensitive lookup
        for name, create_class in cls._create_models.items():
            if name.lower() == entity_name.lower():
                return create_class
        return None
    
    @classmethod
    def get_update_class(cls, entity_name: str) -> Type[Any] | None:
        """Get pre-loaded update class by entity name.
        
        Args:
            entity_name: Entity name (e.g., "User" returns UserUpdate)
            
        Returns:
            Update class or None if not found
            
        Raises:
            RuntimeError: Only if ModelService not initialized
        """
        # Case-insensitive lookup
        for name, update_class in cls._update_models.items():
            if name.lower() == entity_name.lower():
                return update_class
        return None
    
    @classmethod
    def get_available_models(cls) -> list[str]:
        """Get list of available model names."""
        return list(cls._models.keys())