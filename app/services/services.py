"""
Central service initialization and routing.
All services are initialized here and routes registered from main.py startup hook.

This module loads service configurations from MetadataService (parsed from schema.mmd),
uses deterministic naming to load provider classes from app.services, and dynamically
creates API routes based on @expose_endpoint decorators.

Naming convention:
  Service name: "authn.cookies.redis"
  Module: app.services.authn.cookies.redis
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


def normalize_route(route: str) -> str:
    """
    Normalize route and prepend /api prefix.

    Args:
        route: Route string (with or without leading slash)

    Returns:
        Normalized route with /api prefix

    Examples:
        "login" -> "/api/login"
        "/login" -> "/api/login"
        "login/user" -> "/api/login/user"
    """
    # Strip leading/trailing slashes
    route = route.strip('/')
    # Prepend /api
    return f"/api/{route}"


def get_service_module(service_name: str):
    """
    Load service module (lazy cached).

    Args:
        service_name: Service name like "authn.cookies.redis"

    Returns:
        Module object (e.g., app.services.authn.cookies.redis)
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
    """Handles service route registration from entity configs"""

    @staticmethod
    def create_router(service_name: str, module=None, app=None):
        """
        Create routes for a service using entity configs.
        Reads routes from ServiceManager entity configs.

        Args:
            service_name: Service provider like "cookies.redis"
            module: Optional pre-loaded module (avoids re-loading)
            app: Optional FastAPI app to register routes with
        """
        if not app:
            return  # No app to register with

        # Extract service type from full module path
        # e.g., "authn.cookies.redis" -> service_type = "authn"
        parts = service_name.split('.')
        if len(parts) < 2:
            return  # Invalid service name format

        service_type = parts[0]  # First part is the service type

        if service_type not in ServiceManager._service_instances:
            return  # No matching service found

        # Get service data from ServiceManager
        service_data = ServiceManager._service_instances.get(service_type)
        if not service_data:
            return

        service_instance = service_data.get('instance')
        entity_configs = service_data.get('entity_configs', {})

        if not service_instance or not entity_configs:
            return

        # Find methods with @expose_endpoint decorator
        for method_name in dir(service_instance):
            method = getattr(service_instance, method_name)

            if hasattr(method, '_endpoint_metadata'):
                metadata = method._endpoint_metadata
                base_summary = metadata.get('summary', method_name)
                decorator_route = metadata.get('route', '')

                # Hard-coded: login is entity-specific, others are service-level
                if method_name == 'login' and entity_configs:
                    # Register one POST route per entity config
                    for entity, config in entity_configs.items():
                        route_path = config.get('route')
                        if not route_path:
                            continue

                        normalized_route = normalize_route(route_path)
                        summary = f"{base_summary} ({entity})"

                        # Fix closure bug: capture method using default parameter
                        async def handler(request: Request, response: Response, m=method):
                            return await m(request, response)

                        app.post(normalized_route, summary=summary)(handler)
                        print(f"  Registered route: POST {normalized_route} -> {service_type}.{method_name} (entity={entity})")

                elif method_name in ['logout', 'refresh'] and decorator_route:
                    # Service-level POST endpoints
                    normalized_route = normalize_route(decorator_route)

                    # Fix closure bug: capture method using default parameter
                    async def handler(request: Request, response: Response, m=method):
                        return await m(request, response)

                    app.post(normalized_route, summary=base_summary)(handler)
                    print(f"  Registered route: POST {normalized_route} -> {service_type}.{method_name}")

                elif method_name == 'get_session' and decorator_route:
                    # Service-level GET endpoint
                    normalized_route = normalize_route(decorator_route)

                    # Fix closure bug: capture method using default parameter
                    async def handler(request: Request, response: Response, m=method):
                        return await m(request, response)

                    app.get(normalized_route, summary=base_summary)(handler)
                    print(f"  Registered route: GET {normalized_route} -> {service_type}.{method_name}")


class ServiceManager:
    """Handles service lifecycle - initialization and shutdown"""
    _services: List[str] = []
    # New structure: { 'authn': {'provider': 'cookies.redis', 'instance': <class>, 'entity_configs': {...}} }
    _service_instances: Dict[str, Any] = {}

    @staticmethod
    async def initialize(app=None):
        """
        Initialize all services from MetadataService.
        Called once at app startup from main.py

        Args:
            app: FastAPI app instance (optional, for router registration)
        """
        # Get all services from metadata (parsed from schema.mmd)
        # New format: { 'authn': {'provider': 'cookies.redis', 'entity_configs': {'Auth': {...}, 'User': {...}}} }
        services = MetadataService.get_services()
        if not services:
            return

        # Initialize all services (dependency handling removed for now - can add back if needed)
        for service_type, service_data in services.items():
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
        """Get service instance by type (e.g., 'authn', 'authz')"""
        service_data = ServiceManager._service_instances.get(service_type)
        return service_data.get('instance') if service_data else None

    @staticmethod
    def get_service_config(service_type: str, entity: str) -> Dict[str, Any]:
        """Get entity-specific config for a service"""
        service_data = ServiceManager._service_instances.get(service_type)
        if service_data:
            return service_data.get('entity_configs', {}).get(entity, {})
        return {}

    @staticmethod
    async def _start_service(service_type: str, service_data: Dict[str, Any], app=None):
        """Initialize a single service and register its routes"""
        service_provider = service_data.get('provider')
        entity_configs = service_data.get('entity_configs', {})

        try:
            # Construct full module path: service_type.provider
            # e.g., "authn" + "cookies.redis" -> "authn.cookies.redis"
            full_module_path = f"{service_type}.{service_provider}"

            # Load service module
            module = get_service_module(full_module_path)

            # Find service class with initialize method
            service_class = find_service_class(module)

            if service_class:
                # Merge runtime config (Redis host/port/etc) into each entity config
                # Config keys use full module path (e.g., "authn.cookies.redis")
                runtime_config = Config.get(full_module_path, {})

                # Pass entity_configs to initialize method
                await service_class.initialize(entity_configs, runtime_config)

                # Create service instance for endpoint handlers
                service_instance = service_class()

                # Cache the service data (provider, instance, entity_configs)
                ServiceManager._service_instances[service_type] = {
                    'provider': service_provider,
                    'instance': service_instance,
                    'entity_configs': entity_configs
                }

                entities_list = list(entity_configs.keys())
                print(f"✓ {full_module_path} initialized for entities: {entities_list}")
            else:
                # No initialize method - still report the service
                print(f"✓ {full_module_path} loaded (no initialization required)")

            ServiceManager._services.append(service_type)

            # Register routes (create_router handles registration internally)
            ServiceRouter.create_router(full_module_path, module=module, app=app)

        except Exception as e:
            import traceback
            print(f"⚠ Failed to initialize {full_module_path}: {e}")
            traceback.print_exc()

    @staticmethod
    async def shutdown():
        """
        Cleanup all services at app shutdown.
        """
        # Add cleanup logic as services are added
        print("✓ All services shut down")
