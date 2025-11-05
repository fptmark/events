"""
Service endpoint decorators for dynamic route registration.

These decorators mark service methods for automatic API endpoint creation
by the ServiceRouterFactory.
"""


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
