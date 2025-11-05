"""
RBAC (Role-Based Access Control) service for permission management.

Handles permission extraction from sessions and permission checking for CRUD operations.
"""

from typing import Dict, Optional, Any
from app.core.notify import Notification, HTTP
from app.core.metadata import MetadataService
from app.core.request_context import RequestContext
from app.services.services import ServiceManager

class Rbac:
    """RBAC service - utility class with no initialization required"""

    @classmethod
    async def initialize(cls, config: dict, service_config: dict = None):
        """Initialize RBAC service (no-op for utility services)"""
        print(f"  RBAC service loaded (utility service - no initialization required)")
        return cls

    @staticmethod
    async def get(field: str) -> Any:
        """
        Get authorization field from auth service.
        Delegates to auth service for session storage.

        Args:
            field: Field name to retrieve (e.g., "permissions")

        Returns:
            Field value or None if not found
        """
        auth_service = ServiceManager.get_service_instance("auth")
        if not auth_service or not ServiceManager.isServiceStarted("authz"):
            return None

        return await auth_service.get(field)

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
        role_doc = await db.documents.bypass(entity, {'Id': roleId}, settings.get("outputs"))

        if role_doc:
            return json5.loads(role_doc.get('permissions', '{}'))
        return None


    @staticmethod
    async def get_permissions(session_id: str = "") -> Dict[str, str]:
        """
        Extract user permissions from the Auth service session.
        If no session, return read-only access to auth entity (for login).

        Args:
            session_id: Session ID from cookie

        Returns:
            Dict mapping entity names to permission strings (e.g., {"User": "crud", "Account": "r"})
            For unauthenticated users, returns read access to auth entity only
            Empty dict if session expired (absolute max exceeded)
        """
        if not session_id:
            session_id = RequestContext.get_session_id()

        if not session_id:
            return {}

        from app.services.services import ServiceManager

        auth_svc = ServiceManager.get_service_instance("auth")
        if not auth_svc:
            Notification.error(HTTP.INTERNAL_ERROR, "Auth service not found")

        _, rbac_entity, rbac_settings = MetadataService.get_service("authz")
        if not rbac_settings:
            Notification.error(HTTP.INTERNAL_ERROR, "Authz service not found")

        permissions_field = rbac_settings.get("output")
        permissions = await auth_svc.get(permissions_field)

        if not permissions:
            # Get session to retrieve roleId
            auth = await auth_svc.authorized()
            if auth:
                roleId_field = rbac_settings.get("input")
                roleId = auth.get(roleId_field)
                if roleId:
                    permissions = await Rbac._load_permissions_from_role(rbac_entity, rbac_settings, roleId)
                    if permissions:
                        await auth_svc.set(permissions_field, permissions)

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
    async def check_permissions(entity: str, operation: str, auth: Dict, auth_service) -> bool:
        """
        Check if user has permission for the given operation on entity.
        Called by GatingService to validate RBAC permissions.

        Args:
            entity: Entity name being accessed
            operation: Operation type ('c', 'r', 'u', 'd')
            auth: Session data from auth service (contains userId, roleId, permissions, etc.)
            auth_service: Auth service class for accessing cookie store

        Returns:
            True if permission granted, False otherwise
        """
        if not auth:
            return False

        # Get metadata for RBAC service
        _, rbac_entity, rbac_settings = MetadataService.get_service("authz")
        if not rbac_settings:
            return False

        # Get field names from metadata
        permissions_field = rbac_settings.get("outputs")[0]
        input_mappings = rbac_settings.get("inputs", {})

        # Try to get cached permissions from auth service
        permissions = auth.get(permissions_field) or await auth_service.get(permissions_field)

        # If not cached, load from Role entity and cache it
        if not permissions:
            roleId_field = list(input_mappings.keys())[0]
            roleId = auth.get(roleId_field)
            if roleId:
                permissions = await Rbac._load_permissions_from_role(rbac_entity, rbac_settings, roleId)
                if permissions:
                    await auth_service.set(permissions_field, permissions)
                else:
                    return False

        # Check permission using existing has_permission logic
        return Rbac.has_permission(permissions, entity, operation)
