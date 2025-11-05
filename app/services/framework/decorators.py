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
        async def validated_init(cls_or_self, config: dict, *args, **kwargs):
            # Validate config matches schema
            errors = []
            service_name = f"{cls.__module__}.{cls.__name__}"

            # Check entity field
            if cls._service_schema[SCHEMA_ENTITY] and SCHEMA_ENTITY not in config:
                errors.append(f"Missing required field: '{SCHEMA_ENTITY}'")

            # Check inputs structure
            if cls._service_schema[SCHEMA_INPUTS]:
                if SCHEMA_INPUTS not in config:
                    errors.append(f"Missing required field: '{SCHEMA_INPUTS}'")
                else:
                    config_inputs = config.get(SCHEMA_INPUTS, {})
                    for field in cls._service_schema[SCHEMA_INPUTS].keys():
                        if field not in config_inputs:
                            errors.append(f"Missing required input field: '{field}'")

            # Check outputs
            if cls._service_schema[SCHEMA_OUTPUTS]:
                if SCHEMA_OUTPUTS not in config:
                    errors.append(f"Missing required field: '{SCHEMA_OUTPUTS}'")
                elif not isinstance(config[SCHEMA_OUTPUTS], list):
                    errors.append(f"Field '{SCHEMA_OUTPUTS}' must be a list")
                else:
                    config_outputs = config[SCHEMA_OUTPUTS]
                    for field in cls._service_schema[SCHEMA_OUTPUTS]:
                        if field not in config_outputs:
                            errors.append(f"Output field '{field}' not found in config outputs list")

            # Check store fields
            if cls._service_schema[SCHEMA_STORE]:
                if SCHEMA_STORE not in config:
                    errors.append(f"Missing required field: '{SCHEMA_STORE}'")
                elif not isinstance(config[SCHEMA_STORE], list):
                    errors.append(f"Field '{SCHEMA_STORE}' must be a list")
                else:
                    config_store = config[SCHEMA_STORE]
                    for field in cls._service_schema[SCHEMA_STORE]:
                        if field not in config_store:
                            errors.append(f"Store field '{field}' not found in config store list")

            if errors:
                error_msg = f"Service '{service_name}' configuration validation failed:\n"
                error_msg += "\n".join(f"  - {err}" for err in errors)
                print(f"❌ {error_msg}")
                raise ValueError(error_msg)

            # Config is valid - call original initialize
            return await original_init.__func__(cls_or_self, config, *args, **kwargs)

        # Replace with validated version
        cls.initialize = classmethod(validated_init)

        return cls

    return decorator
