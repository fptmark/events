"""
Simplified dynamic router factory that reads entity names from schema.yaml.

This module creates FastAPI routers dynamically based on entity names from schema.yaml,
eliminating the need for metadata services, reflection, or async complexity.
"""

from pathlib import Path
from fastapi import APIRouter, Request
from typing import Dict, Any, List, Optional, Type, Protocol
from pydantic import BaseModel, Field
import logging

from app.routers.router_factory import get_entity_names, ModelImportCache
from app.routers.endpoint_handlers import (
    list_entities_handler, get_entity_handler, create_entity_handler,
    update_entity_handler, delete_entity_handler, EntityModelProtocol
)

logger = logging.getLogger(__name__)


# Generic response models for OpenAPI
def create_response_models(entity_cls: Type[EntityModelProtocol]) -> tuple[Type[BaseModel], Type[BaseModel]]:
    """Create response models dynamically for any entity"""
    entity_name = entity_cls.__name__
    
    # Create response models using class-based approach for better type safety
    class EntityResponse(BaseModel):
        data: Optional[Dict[str, Any]] = None
        # message: Optional[str] = None
        # level: Optional[str] = None
        # metadata: Optional[Dict[str, Any]] = None
        notifications: Optional[Dict[str, Dict[str, Any]]] = None
        status: Optional[str] = None
        summary: Optional[Dict[str, Any]] = None
    
    class EntityListResponse(BaseModel):
        data: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
        # message: Optional[str] = None
        # level: Optional[str] = None
        # metadata: Optional[Dict[str, Any]] = None
        notifications: Optional[Dict[str, Dict[str, Any]]] = None
        status: Optional[str] = None
        summary: Optional[Dict[str, Any]] = None
        pagination: Optional[Dict[str, Any]] = None
    
    # Dynamically set the class names for better OpenAPI docs
    EntityResponse.__name__ = f"{entity_name}Response"
    EntityListResponse.__name__ = f"{entity_name}ListResponse"
    
    return EntityResponse, EntityListResponse


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
            create_cls = ModelImportCache.get_create_class(entity_name)  # type: ignore
            update_cls = ModelImportCache.get_update_class(entity_name)  # type: ignore
        except ImportError as e:
            logger.error(f"Failed to import classes for {entity_name}: {e}")
            # Return empty router if imports fail
            return router
        
        entity_lower = entity_name.lower()
        
        # Create response models for OpenAPI documentation
        EntityResponse, EntityListResponse = create_response_models(entity_cls)
        
        # Use proper FastAPI decorators for better OpenAPI schema generation
        
        @router.get(
            "",
            summary=f"List all {entity_lower}s",
            response_description=f"List of {entity_lower}s with metadata",
            response_model=EntityListResponse,
            responses={
                200: {"description": f"Successfully retrieved {entity_lower} list"},
                500: {"description": "Server error"}
            }
        )
        async def list_entities(request: Request) -> Dict[str, Any]:  # noqa: F811
            return await list_entities_handler(entity_cls, entity_name, request)
        
        @router.get(
            "/{entity_id}",
            summary=f"Get a specific {entity_lower} by ID",
            response_description=f"The requested {entity_lower}",
            response_model=EntityResponse,
            responses={
                200: {"description": f"Successfully retrieved {entity_lower}"},
                404: {"description": f"{entity_name} not found"},
                500: {"description": "Server error"}
            }
        )
        async def get_entity(entity_id: str, request: Request) -> Dict[str, Any]:  # noqa: F811
            return await get_entity_handler(entity_cls, entity_name, entity_id, request)

        @router.post(
            "",
            summary=f"Create a new {entity_lower}",
            response_description=f"The created {entity_lower}",
            response_model=EntityResponse,
            responses={
                200: {"description": f"Successfully created {entity_lower}"},
                422: {"description": "Validation error"},
                409: {"description": "Duplicate entry"},
                500: {"description": "Server error"}
            }
        )
        async def create_entity(entity_data: create_cls) -> Dict[str, Any]:  # noqa: F811
            return await create_entity_handler(entity_cls, entity_name, entity_data)
        
        @router.put(
            "/{entity_id}",
            summary=f"Update an existing {entity_lower}",
            response_description=f"The updated {entity_lower}",
            response_model=EntityResponse,
            responses={
                200: {"description": f"Successfully updated {entity_lower}"},
                404: {"description": f"{entity_name} not found"},
                422: {"description": "Validation error"},
                409: {"description": "Duplicate entry"},
                500: {"description": "Server error"}
            }
        )
        async def update_entity(entity_id: str, entity_data: update_cls) -> Dict[str, Any]:  # noqa: F811
            return await update_entity_handler(entity_cls, entity_name, entity_id, entity_data)
        
        @router.delete(
            "/{entity_id}",
            summary=f"Delete a {entity_lower}",
            response_description="Deletion confirmation",
            response_model=EntityResponse,
            responses={
                200: {"description": f"Successfully deleted {entity_lower}"},
                404: {"description": f"{entity_name} not found"},
                500: {"description": "Server error"}
            }
        )
        async def delete_entity(entity_id: str) -> Dict[str, Any]:  # noqa: F811
            return await delete_entity_handler(entity_cls, entity_name, entity_id)
        
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

