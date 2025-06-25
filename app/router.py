"""
Simplified dynamic router factory that reads entity names from schema.yaml.

This module creates FastAPI routers dynamically based on entity names from schema.yaml,
eliminating the need for metadata services, reflection, or async complexity.
"""

import yaml
from pathlib import Path
from fastapi import APIRouter, Request
from typing import Dict, Any, Type, List
import importlib
import logging
import json
from urllib.parse import unquote
from app.notification import (
    start_notifications, end_notifications, get_notifications,
    notify_success, notify_error, notify_warning, notify_validation_error,
    NotificationType
)
from app.errors import ValidationError, NotFoundError, DuplicateError, DatabaseError

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


class SimpleDynamicRouterFactory:
    """Factory for creating entity-specific routers from schema.yaml entity names."""
    
    # Cache for imported model classes to avoid repeated imports
    _model_class_cache: Dict[str, Type] = {}
    
    @classmethod
    def _import_model_class(cls, entity_name: str) -> Type:
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
    
    @staticmethod
    def _import_create_class(entity_name: str) -> Type:
        """Dynamically import the Create model class."""
        try:
            module_name = f"app.models.{entity_name.lower()}_model"
            module = importlib.import_module(module_name)
            return getattr(module, f"{entity_name}Create")
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import create class {entity_name}Create: {e}")
            raise ImportError(f"Could not import create class {entity_name}Create")
    
    @staticmethod
    def _import_update_class(entity_name: str) -> Type:
        """Dynamically import the Update model class."""
        try:
            module_name = f"app.models.{entity_name.lower()}_model"
            module = importlib.import_module(module_name)
            return getattr(module, f"{entity_name}Update")
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import update class {entity_name}Update: {e}")
            raise ImportError(f"Could not import update class {entity_name}Update")
    
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
        
        # Dynamic model imports
        try:
            entity_cls = cls._import_model_class(entity_name)
            create_cls = cls._import_create_class(entity_name)
            update_cls = cls._import_update_class(entity_name)
        except ImportError as e:
            logger.error(f"Failed to import classes for {entity_name}: {e}")
            # Return empty router if imports fail
            return router
        
        entity_lower = entity_name.lower()
        
        # Helper function to add FK view data to entity dictionaries
        async def add_view_data(entity_dict: Dict[str, Any], view_spec: Dict[str, Any] | None) -> None:
            """Add foreign key data to entity based on view specification."""
            if not view_spec:
                return
                
            try:
                # Process each FK in the view specification
                for fk_name, requested_fields in view_spec.items():
                    fk_id_field = f"{fk_name}Id"
                    
                    # Check if entity has this FK field
                    if fk_id_field in entity_dict and entity_dict[fk_id_field]:
                        try:
                            # Import the related entity class
                            fk_entity_name = fk_name.capitalize()
                            fk_entity_cls = cls._import_model_class(fk_entity_name)
                            
                            # Get the related entity
                            related_entity, _ = await fk_entity_cls.get(entity_dict[fk_id_field])
                            related_data = related_entity.model_dump()
                            
                            # Extract only the requested fields and add exists flag
                            fk_data = {"exists": True}
                            
                            # Handle case-insensitive field matching for URL parameter issues
                            # Some browsers (Chrome/Mac) convert URL params to lowercase
                            field_map = {k.lower(): k for k in related_data.keys()}
                            
                            for field in requested_fields:
                                # Try exact match first, then case-insensitive fallback
                                if field in related_data:
                                    fk_data[field] = related_data[field]
                                elif field.lower() in field_map:
                                    # Use the actual field name from the model
                                    actual_field = field_map[field.lower()]
                                    fk_data[actual_field] = related_data[actual_field]
                            
                            # Add the FK data to the entity
                            entity_dict[fk_name] = fk_data
                            
                        except Exception as fk_error:
                            # Log FK lookup error but don't fail the whole request
                            notify_warning(f"Failed to load {fk_name} for {entity_name}: {str(fk_error)}", NotificationType.DATABASE)
                            # Return an object indicating the FK doesn't exist
                            entity_dict[fk_name] = {"exists": False}
            
            except Exception as view_error:
                # Log view parsing error but continue without FK data
                notify_warning(f"Failed to parse view parameter: {str(view_error)}", NotificationType.VALIDATION)
        
        # LIST endpoint
        async def list_entities(request: Request) -> Dict[str, Any]:
            """List all entities of this type."""
            notifications = start_notifications(entity=entity_name, operation=f"list_{entity_lower}s")
            
            # Extract query parameters for FK processing
            query_params = dict(request.query_params)
            view_param = query_params.get('view')
            view_spec = json.loads(unquote(view_param)) if view_param else None
            
            try:
                entities, validation_errors = await entity_cls.get_all()
                
                # Add any validation errors as warnings
                for error in validation_errors:
                    notify_warning(str(error), NotificationType.VALIDATION)
                
                # Process FK includes if view parameter is provided
                entity_data = []
                for entity in entities:
                    entity_dict = entity.model_dump()
                    await add_view_data(entity_dict, view_spec)
                    entity_data.append(entity_dict)

                return notifications.to_response(entity_data)
            except Exception as e:
                notify_error(f"Failed to retrieve {entity_lower}s: {str(e)}", NotificationType.SYSTEM)
                return notifications.to_response(None)
            finally:
                end_notifications()
        
        # GET endpoint
        async def get_entity(entity_id: str, request: Request) -> Dict[str, Any]:
            """Get a specific entity by ID."""
            notifications = start_notifications(entity=entity_name, operation=f"get_{entity_lower}")
            
            # Extract query parameters for FK processing
            query_params = dict(request.query_params)
            view_param = query_params.get('view')
            view_spec = json.loads(unquote(view_param)) if view_param else None
            
            try:
                entity, warnings = await entity_cls.get(entity_id)
                
                # Add any warnings as notifications
                for warning in warnings:
                    notify_warning(warning, NotificationType.DATABASE)
                
                # Process FK includes if view parameter is provided
                entity_dict = entity.model_dump()
                await add_view_data(entity_dict, view_spec)
                
                return notifications.to_response(entity_dict)
            except NotFoundError:
                notify_error(f"{entity_name} not found", NotificationType.BUSINESS)
                return notifications.to_response(None)
            except Exception as e:
                notify_error(f"Failed to retrieve {entity_lower}: {str(e)}", NotificationType.SYSTEM)
                return notifications.to_response(None)
            finally:
                end_notifications()
        # POST endpoint
        async def create_entity(entity_data) -> Dict[str, Any]:  # Type will be set dynamically
            """Create a new entity."""
            notifications = start_notifications(entity=entity_name, operation=f"create_{entity_lower}")
            
            try:
                # Let model handle all validation and business logic
                entity = entity_cls(**entity_data.model_dump())
                result, warnings = await entity.save()
                # Add any warnings from save operation
                for warning in warnings:
                    notify_warning(warning, NotificationType.DATABASE)
                notify_success(f"{entity_name} created successfully", NotificationType.BUSINESS)
                return notifications.to_response(result.model_dump())
            except (ValidationError, DuplicateError) as e:
                notify_validation_error(f"Failed to create {entity_lower}: {str(e)}")
                return notifications.to_response(None)
            except Exception as e:
                notify_error(f"Failed to create {entity_lower}: {str(e)}", NotificationType.SYSTEM)
                return notifications.to_response(None)
            finally:
                end_notifications()
        
        # PUT endpoint
        async def update_entity(entity_id: str, entity_data) -> Dict[str, Any]:  # Type will be set dynamically
            """Update an existing entity."""
            notifications = start_notifications(entity=entity_name, operation=f"update_{entity_lower}")
            
            try:
                existing, warnings = await entity_cls.get(entity_id)
                # Add any warnings from get operation
                for warning in warnings:
                    notify_warning(warning, NotificationType.DATABASE)
                    
                # Merge payload data into existing entity - model handles all logic
                updated = existing.model_copy(update=entity_data.model_dump())
                result, save_warnings = await updated.save()
                # Add any warnings from save operation
                for warning in save_warnings:
                    notify_warning(warning, NotificationType.DATABASE)
                notify_success(f"{entity_name} updated successfully", NotificationType.BUSINESS)
                return notifications.to_response(result.model_dump())
            except NotFoundError as e:
                notify_error(f"{entity_name} not found", NotificationType.BUSINESS)
                return notifications.to_response(None)
            except (ValidationError, DuplicateError) as e:
                notify_validation_error(f"Failed to update {entity_lower}: {str(e)}")
                return notifications.to_response(None)
            except Exception as e:
                notify_error(f"Failed to update {entity_lower}: {str(e)}", NotificationType.SYSTEM)
                return notifications.to_response(None)
            finally:
                end_notifications()
        
        # DELETE endpoint
        async def delete_entity(entity_id: str) -> Dict[str, Any]:
            """Delete an entity."""
            notifications = start_notifications(entity=entity_name, operation=f"delete_{entity_lower}")
            
            try:
                success, warnings = await entity_cls.delete(entity_id)
                if success:
                    notify_success(f"{entity_name} deleted successfully", NotificationType.BUSINESS)
                for warning in warnings:
                    notify_warning(warning, NotificationType.DATABASE)
                return notifications.to_response(None)
            except NotFoundError:
                notify_error(f"{entity_name} not found", NotificationType.BUSINESS)
                return notifications.to_response(None)
            except Exception as e:
                notify_error(f"Failed to delete {entity_lower}: {str(e)}", NotificationType.SYSTEM)
                return notifications.to_response(None)
            finally:
                end_notifications()
        
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

