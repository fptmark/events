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
