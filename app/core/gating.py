"""
Core gating service for authentication and authorization.

Implements 3-phase gating:
  1. No auth service → no gating at all
  2. Auth service only → validate session exists
  3. Auth + RBAC service → validate session + check permissions
"""

from typing import Optional
from app.core.metadata import MetadataService
from app.core.request_context import RequestContext
from app.core.notify import Notification, HTTP
from app.services.services import ServiceManager


class GatingService:
    """Centralized gating logic for auth and RBAC checks"""

    @staticmethod
    async def permitted(entity: str, operation: str) -> None:
        """
        Check access based on configured services and operation.

        Args:
            entity: Entity name being accessed
            operation: Operation type ('c'=create, 'r'=read, 'u'=update, 'd'=delete)

        Raises:
            StopWorkError: If access is denied (via Notification system)
        """
        if not ServiceManager.isServiceStarted("auth"):
            # Phase 1: No auth service = no gating
            return

        # Get the auth service class instance
        auth_service = ServiceManager.get_service_instance("auth")
        if not auth_service:
            Notification.error(HTTP.INTERNAL_ERROR, "Auth service not found")

        # Check if the session is valid
        auth = await auth_service.authorized()
        if not auth:
            Notification.error(HTTP.UNAUTHORIZED, "Authentication required")

        if not ServiceManager.isServiceStarted("authz"):
            # Phase 2: Auth service exists - validate session only
            return

        # Get the rbac service class instance
        rbac_service = ServiceManager.get_service_instance("authz")
        if not rbac_service:
            Notification.error(HTTP.INTERNAL_ERROR, "RBAC service not found")

        if RequestContext.get_bypass_rbac():
            print("GatingService: Bypassing rbac gating due to RequestContext setting")
            return

        # Use the auth service with the auth info to get the role permissions from rbac service
        # The auth service will get the permissions from the auth store or if they don't exist get them from the rbac service and cache them for next time
        if not await rbac_service.check_permissions(entity, operation, auth, auth_service):
            Notification.error(HTTP.FORBIDDEN, "Unauthorized operation")
