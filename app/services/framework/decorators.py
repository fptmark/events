"""
Service endpoint decorators for dynamic route registration.

These decorators mark service methods for automatic API endpoint creation
by the ServiceRouterFactory.
"""

from functools import wraps
from typing import Dict, List, Optional, Any


# Service configuration structure keys
# These are the canonical field names used in schema.yaml service configs
# Both runtime code and build-time validators import these constants
SCHEMA_ENTITY = "entity"
SCHEMA_INPUTS = "inputs"
SCHEMA_OUTPUTS = "outputs"
SCHEMA_STORE = "store"


def expose_endpoint(method: str, route: str, summary: str = ""):
    """
    Decorator to mark a service method as an API endpoint.

    Args:
        method: HTTP method (e.g., "POST", "GET", "PUT", "DELETE")
        route: Route path (e.g., "/login", "/logout")
        summary: Optional description for API docs

    Example:
        @expose_endpoint(method="POST", route="/login", summary="User login")
        async def login(self, entity_name: str, credentials: dict):
            ...
    """
    def decorator(func):
        setattr(func, "_endpoint_metadata", {
            "method": method,
            "route": route,
            "summary": summary
        })
        return func
    return decorator


def no_permission_required(func):
    """
    Decorator to mark a service method as bypassing RBAC permission checks.

    SECURITY WARNING: Use this decorator ONLY for trusted system operations
    like authentication (login) that must run before user permissions are established.

    Methods marked with this decorator will bypass all RBAC checks.
    All usage should be reviewed during code review.

    Example:
        @expose_endpoint(method="POST", route="/login", summary="User login")
        @no_permission_required
        async def login(self, credentials: dict):
            # This method can access database without permission checks
            ...
    """
    setattr(func, "_no_permission_required", True)
    return func


def service_config(
    entity: bool = False,
    inputs: Optional[Dict[str, type]] = None,
    outputs: Optional[List[str]] = None,
    store: Optional[List[str]] = None
):
    """
    Decorator to declare and validate service configuration requirements.

    This decorator serves as the single source of truth for what a service needs.
    The metadata lives on the class itself - no separate registry file needed.

    Validates configuration at service initialization time and provides build-time
    introspection for schema validation tools.

    Args:
        entity: Service requires 'entity' field in config
        inputs: Required input fields mapping (e.g., {"login": str, "password": str})
        outputs: Required output fields list (e.g., ["permissions"])
        store: Required store fields list (e.g., ["roleId"])

    Example:
        @service_config(
            entity=True,
            inputs={"login": str, "password": str},
            store=["roleId"]
        )
        class Authn:
            @classmethod
            async def initialize(cls, config: dict):
                # Config is pre-validated by decorator
                entity_name = config["entity"]  # Safe - guaranteed to exist
                login_field = config["inputs"]["login"]  # Safe
                ...
    """
    def decorator(cls):
        # Store schema metadata on the class itself
        cls._service_schema = {
            SCHEMA_ENTITY: entity,
            SCHEMA_INPUTS: inputs or {},
            SCHEMA_OUTPUTS: outputs or [],
            SCHEMA_STORE: store or []
        }

        # Wrap initialize method to validate config
        if not hasattr(cls, 'initialize'):
            # Service doesn't have initialize - just store schema and return
            return cls

        original_init = cls.initialize

        @wraps(original_init.__func__ if isinstance(original_init, classmethod) else original_init)
        async def validated_init(cls_or_self, entity_configs: dict, *args, **kwargs):
            # Validate entity_configs matches schema
            # New format: entity_configs = {'Auth': {inputs: {...}, outputs: [...]}, 'User': {...}}
            errors = []
            service_name = f"{cls.__module__}.{cls.__name__}"

            # Validate it's a dict of entity configurations
            if not isinstance(entity_configs, dict):
                errors.append(f"First parameter must be a dict of entity configs")
            else:
                # Validate each entity's configuration
                for entity_name, entity_config in entity_configs.items():
                    if not isinstance(entity_config, dict):
                        errors.append(f"Entity '{entity_name}' config must be a dict")
                        continue

                    # Check inputs structure
                    if cls._service_schema[SCHEMA_INPUTS]:
                        if SCHEMA_INPUTS not in entity_config:
                            errors.append(f"Entity '{entity_name}': Missing required field '{SCHEMA_INPUTS}'")
                        elif not isinstance(entity_config[SCHEMA_INPUTS], dict):
                            errors.append(f"Entity '{entity_name}': Field '{SCHEMA_INPUTS}' must be a dict")
                        else:
                            config_inputs = entity_config[SCHEMA_INPUTS]
                            # Validate that schema's required input fields are present
                            for field in cls._service_schema[SCHEMA_INPUTS].keys():
                                if field not in config_inputs:
                                    errors.append(f"Entity '{entity_name}': Missing required input field '{field}'")

                    # Check outputs
                    if cls._service_schema[SCHEMA_OUTPUTS]:
                        if SCHEMA_OUTPUTS not in entity_config:
                            errors.append(f"Entity '{entity_name}': Missing required field '{SCHEMA_OUTPUTS}'")
                        elif not isinstance(entity_config[SCHEMA_OUTPUTS], list):
                            errors.append(f"Entity '{entity_name}': Field '{SCHEMA_OUTPUTS}' must be a list")
                        # Note: We don't validate output field names match schema exactly
                        # because different entities may return different output fields

                    # Check store fields if specified
                    if cls._service_schema[SCHEMA_STORE]:
                        if SCHEMA_STORE in entity_config:
                            config_store = entity_config[SCHEMA_STORE]
                            if not isinstance(config_store, list):
                                errors.append(f"Entity '{entity_name}': Field '{SCHEMA_STORE}' must be a list")

            if errors:
                error_msg = f"Service '{service_name}' configuration validation failed:\n"
                error_msg += "\n".join(f"  - {err}" for err in errors)
                print(f"❌ {error_msg}")
                raise ValueError(error_msg)

            # Config is valid - call original initialize
            return await original_init.__func__(cls_or_self, entity_configs, *args, **kwargs)

        # Replace with validated version
        cls.initialize = classmethod(validated_init)

        return cls

    return decorator
