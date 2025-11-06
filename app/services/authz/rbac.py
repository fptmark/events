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

    @classmethod
    async def initialize(cls, config: dict):
        """Initialize RBAC service - config comes from decorator framework"""
        cls.service_config = config
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


    @staticmethod
    def has_permission(permissions: Dict[str, str], entity: str, operation: str) -> bool:
        """
        Check if user has permission without raising error (for UI logic).

        Args:
            permissions: User's permission dict
            entity: Entity name
            operation: Single char operation ('c', 'r', 'u', 'd')

        Returns:
            True if permission granted, False otherwise
        """
        if not permissions:
            return False

        # Check entity-specific permission first
        for perm_entity, perm_ops in permissions.items():
            if perm_entity.lower() == entity.lower() or perm_entity == "*":
                return operation in perm_ops or "s" in perm_ops         # "s" is for system - all priv

        return False