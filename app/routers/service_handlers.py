"""
Dynamic service router factory for creating API endpoints from service providers.

This module discovers services configured in entity metadata, loads their provider
classes from the services registry, and dynamically creates API routes based on
@expose_endpoint decorators.
"""

import importlib
import inspect
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, Request, Response, HTTPException

logger = logging.getLogger(__name__)


class ServiceRouterFactory:
    """Factory for creating dynamic service routers based on entity metadata and service registry."""

    _registry_cache = None

    @classmethod
    def load_registry(cls) -> Dict[str, Any]:
        """Load providers registry from JSON file."""
        if cls._registry_cache is None:
            registry_path = Path("app/providers/providers_registry.json")
            with open(registry_path) as f:
                cls._registry_cache = json.load(f)
        return cls._registry_cache

    @classmethod
    def get_service_class(cls, service_name: str):
        """Load service provider class from registry."""
        registry = cls.load_registry()

        if service_name not in registry:
            raise ValueError(f"Service {service_name} not found in registry")

        service_info = registry[service_name]
        module = importlib.import_module(service_info["module"])
        return getattr(module, service_info["class"])

    @classmethod
    def create_service_router(cls, entity_name: str, service_name: str) -> APIRouter:
        """
        Create a router for a specific service on an entity.

        Args:
            entity_name: Entity name (e.g., "User")
            service_name: Service identifier (e.g., "auth.cookies.redis")

        Returns:
            FastAPI router with service endpoints
        """
        # Load service provider class
        service_cls = cls.get_service_class(service_name)
        service_instance = service_cls()

        # Create router
        # Route prefix: /{entity}/auth (extract category from service name)
        category = service_name.split('.')[0]  # "auth.cookies.redis" -> "auth"
        router = APIRouter(
            prefix=f"/{entity_name.lower()}/{category}",
            tags=[f"{entity_name}"]
        )

        # Find all methods with @expose_endpoint decorator
        for method_name in dir(service_instance):
            method = getattr(service_instance, method_name)

            if hasattr(method, '_endpoint_metadata'):
                metadata = method._endpoint_metadata
                http_method = metadata['method'].upper()
                route = metadata['route']
                summary = metadata.get('summary', '')

                # Create endpoint handler that wraps the service method
                def create_handler(svc_method, svc_cls, ent_name):
                    async def handler(request: Request, response: Response):
                        # Determine method signature to know what to pass
                        sig = inspect.signature(svc_method)
                        params = list(sig.parameters.keys())

                        # If method expects credentials/body (like login), parse JSON
                        if 'credentials' in params or len(params) > 2:
                            body = await request.json()
                            result = await svc_method(ent_name, body)
                        # Otherwise pass the request object (like logout, refresh)
                        else:
                            result = await svc_method(request)

                        # Handle response based on service type
                        if isinstance(result, str):  # session_id from login
                            response.set_cookie(
                                key=svc_cls.cookie_name,
                                value=result,
                                **svc_cls.cookie_options
                            )
                            return {"success": True, "message": "Login successful"}
                        elif isinstance(result, bool):
                            if svc_method.__name__ == "logout" and result:
                                response.delete_cookie(key=svc_cls.cookie_name)
                                return {"success": True, "message": "Logout successful"}
                            elif result:
                                return {"success": True, "message": "Operation successful"}
                            else:
                                raise HTTPException(status_code=401, detail="Operation failed")

                        return result

                    return handler

                # Register route
                handler_func = create_handler(method, service_cls, entity_name)

                if http_method == "POST":
                    router.post(route, summary=summary)(handler_func)
                elif http_method == "GET":
                    router.get(route, summary=summary)(handler_func)
                elif http_method == "PUT":
                    router.put(route, summary=summary)(handler_func)
                elif http_method == "DELETE":
                    router.delete(route, summary=summary)(handler_func)

        return router

    @classmethod
    def create_all_service_routers(cls) -> List[APIRouter]:
        """
        Scan all entities and create routers for their configured services.

        Returns:
            List of service routers
        """
        from app.services.metadata import MetadataService

        routers = []
        entities = MetadataService.list_entities()

        for entity_name in entities:
            metadata = MetadataService.get(entity_name)
            services = metadata.get("services", {})

            for service_name in services:
                try:
                    router = cls.create_service_router(entity_name, service_name)
                    routers.append(router)
                    logger.info(f"Created service router: {entity_name}/{service_name}")
                except Exception as e:
                    logger.warning(f"Failed to create service router for {entity_name}/{service_name}: {e}")

        return routers


# Convenience function for easy integration
def get_all_service_routers() -> List[APIRouter]:
    """
    Get all dynamic service routers for entities with configured services.

    This is the main entry point for getting service routers.
    Call this from services_init.py to register service routes.

    Returns:
        List of FastAPI routers ready to be registered
    """
    return ServiceRouterFactory.create_all_service_routers()
