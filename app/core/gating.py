"""
Core gating service for authentication and authorization.

Implements 3-phase gating:
  1. No authn service → no gating at all
  2. authn service only → validate session exists
  3. authn + authz service → validate session + check permissions
"""

from typing import Optional
from app.core.metadata import MetadataService
from app.core.request_context import RequestContext
from app.core.notify import Notification, HTTP
from app.services.services import ServiceManager
from app.services.authz.rbac import Rbac


class GatingService:
    """Centralized gating logic for authn and authz checks"""

    @staticmethod
    async def permitted(entity: str, operation: str) -> None:
        """
        Check access based on configured services and operation.

        Args:
            entity: Entity name being accessed
            operation: Operation type ('c'=create, 'r'=read, 'u'=update, 'd'=delete)

        Raises:
            StopWorkError: If access is denied (via Notification system)

        Note: Permissions are enriched into the authn session at login by the authz service.
        """
        if not ServiceManager.isServiceStarted("authn"):
            # Phase 1: No authn service = no gating
            return

        # Get the authn service class instance
        authn_service = ServiceManager.get_service_instance("authn")
        if not authn_service:
            Notification.error(HTTP.INTERNAL_ERROR, "Authentication service internal error")

        # Check if the session is valid
        authn = await authn_service.authorized()
        if not authn:
            Notification.error(HTTP.UNAUTHORIZED, "Authentication required")

        if not ServiceManager.isServiceStarted("authz"):
            # Phase 2: authz service not started - validate session only
            return

        # Phase 3: authz enabled - check permissions
        # Permissions are already in authn object (enriched at login)
        permissions = authn.get('permissions', None)
        if permissions is None:
            Notification.error(HTTP.INTERNAL_ERROR, "Permissions missing from authn data")

        # Check permission
        if not Rbac.has_permission(permissions, entity, operation):
            Notification.error(HTTP.FORBIDDEN, "Unauthorized operation")
    