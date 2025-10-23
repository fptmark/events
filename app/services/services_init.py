"""
Central service initialization.
All services are initialized here and called from main.py startup hook.
"""
from app.config import Config
from app.services.auth.cookies.redis_provider import CookiesAuth


async def initialize(app=None):
    """
    Initialize all services.
    Called once at app startup from main.py

    Args:
        app: FastAPI app instance (optional, for router registration)
    """
    # Initialize Redis auth service
    redis_config = Config.get("auth.cookies.redis", {})
    await CookiesAuth.initialize(redis_config)
    print("✓ Redis auth service initialized")

    # Register service routers
    if app:
        from app.services.redis_user import init_router as init_user_auth_router
        init_user_auth_router(app)
        print("✓ Service routers registered")

    # Future services can be added here:
    # await NotificationService.initialize(...)
    # await AnalyticsService.initialize(...)

    print("✓ All services initialized")


async def shutdown():
    """
    Cleanup all services at app shutdown.
    """
    # Add cleanup logic as services are added
    # For example: await CookiesAuth.shutdown()
    print("✓ All services shut down")
