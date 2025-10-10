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

from app.services.model import ModelService
from app.routers.endpoint_handlers import (
    get_all_handler, get_entity_handler, create_entity_handler,
    update_entity_handler, delete_entity_handler, EntityModelProtocol
)

logger = logging.getLogger(__name__)


# Generic response models for OpenAPI
def create_response_models(entity_cls: Type[EntityModelProtocol]) -> tuple[Type[BaseModel], Type[BaseModel]]:
    """Create response models dynamically for any entity"""
    entity_type = entity_cls.__name__
    
    # Create response models using class-based approach for better type safety
    class EntityResponse(BaseModel):
        data: Optional[Dict[str, Any]] = None
        notifications: Optional[Dict[str, Any]] = None
        status: Optional[str] = None
        summary: Optional[Dict[str, Any]] = None
    
    class EntityAllResponse(BaseModel):
        data: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
        notifications: Optional[Dict[str, Any]] = None
        status: Optional[str] = None
        summary: Optional[Dict[str, Any]] = None
        pagination: Optional[Dict[str, Any]]
    
    # Dynamically set the class names for better OpenAPI docs
    EntityResponse.__name__ = f"{entity_type}Response"
    EntityAllResponse.__name__ = f"{entity_type}AllResponse"
    
    return EntityResponse, EntityAllResponse


class SimpleDynamicRouterFactory:
    """Factory for creating entity-specific routers from schema.yaml entity names."""
    
    @classmethod
    def create_entity_router(cls, entity_type: str) -> APIRouter:
        """
        Create a complete CRUD router for an entity.
        
        Args:
            entity_type: The entity name (e.g., "User", "Account")
            
        Returns:
            FastAPI router with all CRUD endpoints for the entity
        """
        # Create router with lowercase prefix but also register uppercase route
        router = APIRouter(
            prefix=f"/{entity_type.lower()}", 
            tags=[entity_type]
        )
        
        # Dynamic model imports using cached factory
        try:
            entity_cls = ModelService.get_model_class(entity_type)
            create_cls = ModelService.get_create_class(entity_type)  # type: ignore
            update_cls = ModelService.get_update_class(entity_type)  # type: ignore
        except ImportError as e:
            logger.error(f"Failed to import classes for {entity_type}: {e}")
            # Return empty router if imports fail
            return router
        
        entity_lower = entity_type
        
        # Create response models for OpenAPI documentation
        EntityResponse, EntityAllResponse = create_response_models(entity_cls) # type: ignore
        
        # Use proper FastAPI decorators for better OpenAPI schema generation
        
        @router.get(
            "",
            summary=f"Get all {entity_lower}s",
            response_description=f"List of {entity_lower}s with metadata",
            response_model=EntityAllResponse,
            responses={
                200: {"description": f"Successfully retrieved {entity_lower} list"},
                500: {"description": "Server error"}
            }
        )
        async def get_all(request: Request) -> Dict[str, Any]:  # noqa: F811
            return await get_all_handler(entity_cls, request)
        
        @router.get(
            "/{entity_id}",
            summary=f"Get a specific {entity_lower} by ID",
            response_description=f"The requested {entity_lower}",
            response_model=EntityResponse,
            responses={
                200: {"description": f"Successfully retrieved {entity_lower}"},
                404: {"description": f"{entity_type} not found"},
                500: {"description": "Server error"}
            }
        )
        async def get_entity(entity_id: str, request: Request) -> Dict[str, Any]:  # noqa: F811
            return await get_entity_handler(entity_cls, entity_id, request)

        @router.post(
            "",
            summary=f"Create a new {entity_lower}",
            response_description=f"The created {entity_lower}",
            response_model=EntityResponse,
            status_code=201,
            responses={
                201: {"description": f"Successfully created {entity_lower}"},
                422: {"description": "Validation error"},
                409: {"description": "Duplicate entry"},
                500: {"description": "Server error"}
            }
        )
        async def create_entity(entity_data: create_cls, request: Request) -> Dict[str, Any]:  # type: ignore # noqa: F811
            return await create_entity_handler(entity_cls, entity_data, request)
        
        @router.put(
            "/{entity_id}",
            summary=f"Update an existing {entity_lower}",
            response_description=f"The updated {entity_lower}",
            response_model=EntityResponse,
            responses={
                200: {"description": f"Successfully updated {entity_lower}"},
                404: {"description": f"{entity_type} not found"},
                422: {"description": "Validation error"},
                409: {"description": "Duplicate entry"},
                500: {"description": "Server error"}
            }
        )
        async def update_entity(entity_id: str, entity_data: update_cls, request: Request) -> Dict[str, Any]:  # type: ignore # noqa: F811
            return await update_entity_handler(entity_cls, entity_id, entity_data, request)
        
        @router.delete(
            "/{entity_id}",
            summary=f"Delete a {entity_lower}",
            response_description="Deletion confirmation",
            response_model=EntityResponse,
            responses={
                200: {"description": f"Successfully deleted {entity_lower}"},
                404: {"description": f"{entity_type} not found"},
                500: {"description": "Server error"}
            }
        )
        async def delete_entity(entity_id: str) -> Dict[str, Any]:  # noqa: F811
            return await delete_entity_handler(entity_cls, entity_id)
        
        # logger.info(f"Created dynamic router for entity: {entity_type}")
        return router
    
    @classmethod
    def create_all_routers(cls, schema_path: Path) -> List[APIRouter]:
        """
        Create routers for all entities found in schema.yaml.
        
        Returns:
            List of FastAPI routers, one for each entity
        """
        entity_types = ModelService.get_available_models()
        routers = []

        for entity_type in entity_types:
            try:
                router = cls.create_entity_router(entity_type)
                routers.append(router)
                # logger.info(f"Successfully created router for: {entity_type}")
            except Exception as e:
                logger.warning(f"Skipping {entity_type} - failed to create router: {e}")
                continue
        
        logger.info(f"Created {len(routers)} dynamic routers from {len(entity_type)} entities")
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

