"""
Simplified dynamic router factory that reads entity names from schema.yaml.

This module creates FastAPI routers dynamically based on entity names from schema.yaml,
eliminating the need for metadata services, reflection, or async complexity.
"""

from pathlib import Path
from fastapi import APIRouter, Request
from typing import Dict, Any, List
import logging

from app.routers.router_factory import get_entity_names, ModelImportCache
from app.routers.endpoint_handlers import (
    list_entities_handler, get_entity_handler, create_entity_handler,
    update_entity_handler, delete_entity_handler
)

logger = logging.getLogger(__name__)


class SimpleDynamicRouterFactory:
    """Factory for creating entity-specific routers from schema.yaml entity names."""
    
    @classmethod
    def create_entity_router(cls, entity_name: str) -> APIRouter:
        """
        Create a complete CRUD router for an entity.
        
        Args:
            entity_name: The entity name (e.g., "User", "Account")
            
        Returns:
            FastAPI router with all CRUD endpoints for the entity
        """
        router = APIRouter(
            prefix=f"/{entity_name.lower()}", 
            tags=[entity_name]
        )
        
        # Dynamic model imports using cached factory
        try:
            entity_cls = ModelImportCache.get_model_class(entity_name)
            create_cls = ModelImportCache.get_create_class(entity_name)
            update_cls = ModelImportCache.get_update_class(entity_name)
        except ImportError as e:
            logger.error(f"Failed to import classes for {entity_name}: {e}")
            # Return empty router if imports fail
            return router
        
        entity_lower = entity_name.lower()
        
        # Create endpoint handlers using the reusable functions
        async def list_entities(request: Request) -> Dict[str, Any]:
            return await list_entities_handler(entity_cls, entity_name, request)
        
        async def get_entity(entity_id: str, request: Request) -> Dict[str, Any]:
            return await get_entity_handler(entity_cls, entity_name, entity_id, request)

        async def create_entity(entity_data) -> Dict[str, Any]:
            return await create_entity_handler(entity_cls, entity_name, entity_data)
        
        async def update_entity(entity_id: str, entity_data) -> Dict[str, Any]:
            return await update_entity_handler(entity_cls, entity_name, entity_id, entity_data)
        
        async def delete_entity(entity_id: str) -> Dict[str, Any]:
            return await delete_entity_handler(entity_cls, entity_name, entity_id)
        
        # Register routes with proper typing for OpenAPI
        router.add_api_route(
            "",
            list_entities,
            methods=["GET"],
            summary=f"List all {entity_lower}s",
            response_description=f"List of {entity_lower}s"
        )
        
        router.add_api_route(
            "/{entity_id}",
            get_entity,
            methods=["GET"],
            summary=f"Get a specific {entity_lower} by ID",
            response_description=f"The requested {entity_lower}"
        )
        
        # Set proper type annotations for OpenAPI
        create_entity.__annotations__['entity_data'] = create_cls
        create_entity.__annotations__['return'] = Dict[str, Any]
        
        update_entity.__annotations__['entity_data'] = update_cls
        update_entity.__annotations__['return'] = Dict[str, Any]
        
        router.add_api_route(
            "",
            create_entity,
            methods=["POST"],
            summary=f"Create a new {entity_lower}",
            response_description=f"The created {entity_lower}"
        )
        
        router.add_api_route(
            "/{entity_id}",
            update_entity,
            methods=["PUT"],
            summary=f"Update an existing {entity_lower}",
            response_description=f"The updated {entity_lower}"
        )
        
        router.add_api_route(
            "/{entity_id}",
            delete_entity,
            methods=["DELETE"],
            summary=f"Delete a {entity_lower}",
            response_description="Deletion confirmation"
        )
        
        logger.info(f"Created dynamic router for entity: {entity_name}")
        return router
    
    @classmethod
    def create_all_routers(cls, schema_path: Path) -> List[APIRouter]:
        """
        Create routers for all entities found in schema.yaml.
        
        Returns:
            List of FastAPI routers, one for each entity
        """
        entity_names = get_entity_names(schema_path)
        routers = []
        
        for entity_name in entity_names:
            try:
                router = cls.create_entity_router(entity_name)
                routers.append(router)
                logger.info(f"Successfully created router for: {entity_name}")
            except Exception as e:
                logger.warning(f"Skipping {entity_name} - failed to create router: {e}")
                continue
        
        logger.info(f"Created {len(routers)} dynamic routers from {len(entity_names)} entities")
        return routers


# Convenience function for easy integration
def get_all_dynamic_routers(schema_path: Path) -> List[APIRouter]:
    """
    Get all dynamic routers for entities in schema.yaml.
    
    This is the main entry point for getting dynamic routers.
    Call this at module level in main.py.
    
    Returns:
        List of FastAPI routers ready to be registered
    """
    return SimpleDynamicRouterFactory.create_all_routers(schema_path)

