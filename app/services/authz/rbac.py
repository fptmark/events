"""
RBAC (Role-Based Access Control) service for permission management.

Handles permission extraction from sessions and permission checking for CRUD operations.
"""

from typing import Dict, Optional, Any
from app.core.notify import Notification, HTTP
from app.core.metadata import MetadataService
from app.core.request_context import RequestContext
from app.services.services import ServiceManager
from app.services.framework import decorators

from app.db.factory import DatabaseFactory
import json5

@decorators.service_config(
    entity=True,
    inputs={"Id": str},
    outputs=["permissions"]
)
class Rbac:
    """RBAC service - utility class for permission management"""

    service_config = None  # Set by decorator during initialization
    _permissions_cache: Dict[str, Dict[str, Any]] = {}  # Cache expanded permissions by roleId

    @classmethod
    async def initialize(cls, config: dict):
        """Initialize RBAC service - config comes from decorator framework"""
        cls.service_config = config
        cls._permissions_cache = {}  # Reset cache on initialization
        print(f"  RBAC service configured for entity: {config.get('entity', 'Missing')}")
        return cls

    @classmethod
    async def permissions(cls, roleId: str) -> Optional[Dict[str, str]]:
        """
        Load permissions from Role entity by roleId (called at login only).

        Args:
            roleId: Role ID to query

        Returns:
            Permissions dict like {"*": "cruds"} or None
        """
        if not cls.service_config:
            print("ERROR: Rbac service not initialized - service_config is None")
            return None

        # Get actual entity name and field mappings from service_config (not decorator schema)
        entity = cls.service_config.get(decorators.SCHEMA_ENTITY)
        input_mappings = cls.service_config.get(decorators.SCHEMA_INPUTS, {})
        output_fields = cls.service_config.get(decorators.SCHEMA_OUTPUTS, [])

        if not entity or not input_mappings or not output_fields:
            print(f"ERROR: Rbac service_config missing required fields: entity={entity}, inputs={input_mappings}, outputs={output_fields}")
            return None

        # Get field names from mappings
        input_field = list(input_mappings.keys())[0]
        output_field = output_fields[0]

        db = DatabaseFactory.get_instance()
        role_doc = await db.documents.bypass(entity, {input_field: roleId}, [output_field])

        if role_doc and role_doc.get(output_field):
            return json5.loads(role_doc[output_field])
        return None

    @classmethod
    async def get_permissions(cls, roleId: str) -> Optional[dict]:
        """
        Get expanded permissions for roleId (cached).

        Uses standard cache-miss pattern - compute once per role, cache forever.
        Cache is cleared on service initialization (server restart).

        Expanded format: {
            "dashboard": ["User", "Account", "Auth"],
            "entity": {"User": "cru", "Account": "cru", "Auth": "r"},
            "reports": [
                {"name": "text", "link": "/api/report...", "location": 1},
                {"name": "text", "link": "/api/report...", "location": -1}
            ]
        }

        Report location: 1, 2, ... = position from left; -1, -2, ... = position from right
        TODO: Implement report population logic

        Logic: Specific entity permissions override wildcard (order-independent)
        Empty string means no access (entity not included)

        Args:
            roleId: Role ID to fetch permissions for

        Returns:
            Expanded permissions structure for UI and server consumption
        """
        # Cache hit - return immediately
        if roleId in cls._permissions_cache:
            return cls._permissions_cache[roleId]

        # Cache miss - compute and cache
        # Get raw permissions from database
        raw_permissions = await cls.permissions(roleId)
        if not raw_permissions:
            result = {"dashboard": [], "entity": {}, "reports": []}
            cls._permissions_cache[roleId] = result
            return result

        # Get all entity types from metadata
        all_entities = MetadataService.list_entities()

        # Build entity permissions (specific overrides wildcard)
        entity_perms = {}
        dashboard_entities = []

        for entity in all_entities:
            # Check for specific entity permission (case-insensitive)
            perm = None
            for key, value in raw_permissions.items():
                if key.lower() == entity.lower():
                    perm = value
                    break

            # If no specific permission, use wildcard
            if perm is None:
                perm = raw_permissions.get("*", "")

            # Only include entities with non-empty permissions
            if perm and perm != "":
                entity_perms[entity] = perm
                dashboard_entities.append(entity)

        result = {
            "dashboard": dashboard_entities,
            "entity": entity_perms,
            "reports": []  # TODO: Populate based on role/permissions
        }

        # Cache result
        cls._permissions_cache[roleId] = result
        return result

    @classmethod
    async def permitted(cls, roleId: str, entity: str, operation: str) -> bool:
        """
        Check if role has permission for entity operation (main authorization check).

        Args:
            roleId: Role ID from session
            entity: Entity name
            operation: Single char operation ('c', 'r', 'u', 'd', 's')

        Returns:
            True if permission granted, False otherwise
        """
        # Get cached permissions for role
        permissions = await cls.get_permissions(roleId)
        if not permissions:
            return False

        # Check permission using expanded structure
        return cls.has_permission(permissions, entity, operation)

    @staticmethod
    def has_permission(permissions: Dict[str, Any], entity: str, operation: str) -> bool:
        """
        Check if permissions dict grants access to entity operation.

        Args:
            permissions: Expanded permissions structure from get_permissions()
                        {"dashboard": [...], "entity": {"User": "cru"}, "reports": [...]}
            entity: Entity name
            operation: Single char operation ('c', 'r', 'u', 'd', 's')

        Returns:
            True if permission granted, False otherwise
        """
        if not permissions:
            return False

        # Extract entity permissions map from expanded structure
        entity_perms = permissions.get("entity", {})
        if not entity_perms:
            return False

        # Check for entity permission (case-insensitive)
        for perm_entity, perm_ops in entity_perms.items():
            if perm_entity.lower() == entity.lower():
                return operation in perm_ops or "s" in perm_ops  # "s" is for system - all priv

        return False