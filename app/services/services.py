"""
Central service initialization and routing.
All services are initialized here and routes registered from main.py startup hook.

This module loads service configurations from MetadataService (parsed from schema.mmd),
uses deterministic naming to load provider classes from app.services, and dynamically
creates API routes based on @expose_endpoint decorators.

Naming convention:
  Service name: "auth.cookies.redis"
  Module: app.services.auth.cookies.redis
  Class: Scanned for classes with @expose_endpoint decorators
"""
import importlib
import inspect
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Request, Response

from app.core.config import Config
from app.core.metadata import MetadataService
from app.core.notify import Notification, HTTP


logger = logging.getLogger(__name__)

# Module cache
_module_cache: Dict[str, Any] = {}


def get_service_module(service_name: str):
    """
    Load service module (lazy cached).

    Args:
        service_name: Service name like "auth.cookies.redis"

    Returns:
        Module object (e.g., app.services.auth.cookies.redis)
    """
    try:
        return _module_cache[service_name]
    except KeyError:
        # Cache miss - load module
        module_path = f"app.services.{service_name}"
        module = importlib.import_module(module_path)
        _module_cache[service_name] = module
        return module


def find_service_class(module):
    """
    Find the first class in a module that has an 'initialize' method.

    Returns:
        Service class or None
    """
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if inspect.isclass(attr) and hasattr(attr, '__module__') and attr.__module__ == module.__name__:
            if hasattr(attr, 'initialize'):
                return attr
    return None


class ServiceRouter:
    """Handles service route registration from @expose_endpoint decorators"""

    @staticmethod
    def create_router(service_name: str, module=None, app=None):
        """
        Create a router for a service using decorator routes.
        Scans module for any @expose_endpoint decorated methods - class-agnostic.

        Args:
            service_name: Service name like "auth.cookies.redis"
            module: Optional pre-loaded module (avoids re-loading)
            app: Optional FastAPI app to register router with
        """
        # Load service module if not provided
        if module is None:
            module = get_service_module(service_name)

        # Use /api prefix - decorator's route is appended as-is
        router = APIRouter(prefix="/api", tags=[service_name.split('.')[0].capitalize()])

        routes_found = False

        # Scan module for any objects with @expose_endpoint decorators
        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            # Check if it's a class
            if inspect.isclass(attr) and hasattr(attr, '__module__') and attr.__module__ == module.__name__:
                # Instantiate and check its methods
                try:
                    instance = attr()
                    for method_name in dir(instance):
                        method = getattr(instance, method_name)

                        if hasattr(method, '_endpoint_metadata'):
                            routes_found = True
                            metadata = method._endpoint_metadata
                            http_method = metadata['method'].upper()
                            route = metadata['route']
                            summary = metadata.get('summary', method_name)

                            # Create endpoint handler
                            def create_handler(svc_method):
                                async def handler(request: Request, response: Response):
                                    return await svc_method(request, response)

                                return handler

                            # Register route with HTTP method
                            handler_func = create_handler(method)

                            if http_method == "POST":
                                router.post(route, summary=summary)(handler_func)
                            elif http_method == "GET":
                                router.get(route, summary=summary)(handler_func)
                            elif http_method == "PUT":
                                router.put(route, summary=summary)(handler_func)
                            elif http_method == "DELETE":
                                router.delete(route, summary=summary)(handler_func)
                except Exception:
                    # Skip classes that can't be instantiated
                    pass

        # Register router with app if routes found and app provided
        if routes_found and app:
            app.include_router(router)


class ServiceManager:
    """Handles service lifecycle - initialization and shutdown"""
    _services: List[str] = []
    _service_instances: Dict[str, Any] = {}  # Cache service instances by type

    @staticmethod
    async def initialize(app=None):
        """
        Initialize all services from MetadataService.
        Called once at app startup from main.py

        Args:
            app: FastAPI app instance (optional, for router registration)
        """
        # Get all services from metadata (parsed from schema.mmd)
        services = MetadataService.get_services()
        if not services:
            return

        # Find all independent services and start them before any dependent services
        for service_type, service_data in services.items():
            if 'depends' not in service_data.get('settings'):
                await ServiceManager._start_service(service_type, service_data, app)

        for service_type, service_data in services.items():
            if 'depends' in service_data.get('settings'):
                await ServiceManager._start_service(service_type, service_data, app)

        print(f"✓ Initialized {ServiceManager._services}")

        if len(services) != len(ServiceManager._services):
            msg = f"Some services failed to initialize.  Services configured: {list(services.keys())}" 
            print(f"⚠ {msg}")
            Notification.error(HTTP.INTERNAL_ERROR, msg)

    @staticmethod
    def isServiceStarted(service_type: str) -> bool:
        """Check if a service is already started"""
        return service_type in ServiceManager._services

    @staticmethod
    def get_service_instance(service_type: str) -> Any:
        """Get service instance by type (e.g., 'auth', 'rbac')"""
        return ServiceManager._service_instances.get(service_type)

    @staticmethod
    async def _start_service(service_type: str, service_data: Dict[str, Any], app=None):
        """Initialize a single service and register its routes"""
        service_provider = service_data.get('provider')

        try:
            # Load service module
            module = get_service_module(service_provider)

            # Find service class with initialize method
            service_class = find_service_class(module)

            if service_class:
                # Get config from Config (e.g., Redis connection settings) and merge with service-specific settings
                settings = service_data.get('settings', {}).copy()

                # Add entity from top-level of service_data
                if 'entity' in service_data:
                    settings['entity'] = service_data['entity']

                # Merge in runtime config (Redis host/port/etc)
                for key, value in Config.get(service_provider, {}).items():
                    settings.setdefault(key, value)

                # Initialize the service
                await service_class.initialize(settings)

                # Cache the service class for later access
                ServiceManager._service_instances[service_type] = service_class
                print(f"✓ {service_provider} initialized")
            else:
                # No initialize method - still report the service
                print(f"✓ {service_provider} loaded (no initialization required)")

            ServiceManager._services.append(service_type)

            # Register routes (create_router handles registration internally)
            ServiceRouter.create_router(service_provider, module=module, app=app)

        except Exception as e:
            print(f"⚠ Failed to initialize {service_provider}: {e}")

    @staticmethod
    async def shutdown():
        """
        Cleanup all services at app shutdown.
        """
        # Add cleanup logic as services are added
        print("✓ All services shut down")
