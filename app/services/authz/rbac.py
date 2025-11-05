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

@decorators.service_config(
    entity=True,
    inputs={"roleId": str},
    outputs=["permissions"]
)
class Rbac:
    """RBAC service - utility class with no initialization required"""

    @classmethod
    async def initialize(cls, config: dict, service_config: dict = None):
        """Initialize RBAC service (no-op for utility services)"""
        print(f"  RBAC service loaded (utility service - no initialization required)")
        return cls

    @staticmethod
    async def _load_permissions_from_role(entity: str, settings: {}, roleId: str) -> Optional[Any]:
        """
        Load permissions from Role entity by roleId.
        Helper method to avoid duplication.

        Args:
            roleId: Role ID to query

        Returns:
            Permissions dict or None if not found such as "{ '*': 'cru'}"
        """
        from app.db.factory import DatabaseFactory
        import json5

        db = DatabaseFactory.get_instance()
        role_doc = await db.documents.bypass(entity, {'Id': roleId}, settings.get(decorators.SCHEMA_OUTPUTS))

        if role_doc:
            return json5.loads(role_doc.get('permissions', '{}'))
        return None


    @staticmethod
    async def get_permissions(session_id: str = "") -> Dict[str, str]:
        """
        Get user permissions from the authn service session.
        Permissions are loaded at login via add_permissions(), so this just retrieves them.

        Args:
            session_id: Session ID from cookie (optional, will use RequestContext if not provided)

        Returns:
            Dict mapping entity names to permission strings (e.g., {"User": "crud", "Account": "r"})
            Empty dict if no session or permissions not found
        """
        if not session_id:
            session_id = RequestContext.get_session_id()

        if not session_id:
            return {}

        from app.services.services import ServiceManager

        authn_svc = ServiceManager.get_service_instance("authn")
        if not authn_svc:
            return {}

        _, _, rbac_settings = MetadataService.get_service("authz")
        if not rbac_settings:
            return {}

        permissions_field = rbac_settings.get(decorators.SCHEMA_OUTPUTS)[0]
        permissions = await authn_svc.get(permissions_field)

        return permissions or {}

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
                return operation in perm_ops

        return False

    @staticmethod
    async def add_permissions(authn_store: Dict) -> None:
        """
        Add permissions to authn store dict for caching.
        Used by authn service when creating sessions.

        Args:
            authn_store: Authn store dict to add permissions to (modified in place)
        """
        # Load from Role entity and cache it
        _, rbac_entity, rbac_settings = MetadataService.get_service("authz")
        if not rbac_settings:
            return  # Can't add permissions without metadata

        input_mappings = rbac_settings.get(decorators.SCHEMA_INPUTS, {})
        permissions_field = rbac_settings.get(decorators.SCHEMA_OUTPUTS)[0]

        roleId_field = list(input_mappings.keys())[0]
        roleId = authn_store.get(roleId_field)
        if roleId:
            permissions = await Rbac._load_permissions_from_role(rbac_entity, rbac_settings, roleId)
            if permissions:
                authn_store[permissions_field] = permissions