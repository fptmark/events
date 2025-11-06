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


class GatingService:
    """Centralized gating logic for authn and authz checks"""

    @staticmethod
    async def permitted(entity: str, operation: str) -> None:
        """
        Check access based on configured services and operation.

        Args:
            entity: Entity name being accessed
            operation: Operation type ('c'=create, 'r'=read, 'u'=update, 'd'=delete, 's'=system)

        Raises:
            StopWorkError: If access is denied (via Notification system)

        Note: Session is already fetched and cached in RC by parse_request_context
        """
        session = RequestContext.get_session()
        if session:
            permissions = session.get('permissions') or None
            authz_svc = ServiceManager.get_service_instance("authz")
            if authz_svc and permissions:   # should not have permissions w/o authz
                if authz_svc.has_permission(permissions, entity, operation):
                    return
                else:
                    Notification.error(HTTP.FORBIDDEN, "Unauthorized operation")
            elif authz_svc:
                Notification.error(HTTP.INTERNAL_ERROR, "Missing permissions")
        else:
            authn_svc = ServiceManager.get_service_instance("authn")
            if authn_svc:
                Notification.error(HTTP.UNAUTHORIZED, "Authentication required")
