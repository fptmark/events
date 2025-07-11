from contextlib import asynccontextmanager
import sys
import argparse
from pathlib import Path
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import app.utils as utils
from app.config import Config
from app.db import DatabaseFactory
from app.db.initializer import DatabaseInitializer
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.errors import (
    DatabaseError, 
    ValidationError, 
    NotFoundError, 
    DuplicateError, 
)

from app.routers.router import get_all_dynamic_routers

from app.services.auth.cookies.redis_provider import CookiesAuth as Auth

from app.models.account_model import Account
from app.models.user_model import User
from app.models.profile_model import Profile
from app.models.tagaffinity_model import TagAffinity
from app.models.event_model import Event
from app.models.userevent_model import UserEvent
from app.models.url_model import Url
from app.models.crawl_model import Crawl

import logging

def setup_routers(yaml_file: str):
    # --- Dynamic Registration of Routers for Entities --- #
    for router in get_all_dynamic_routers(Path(yaml_file)):
        app.include_router(router, prefix="/api")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Events API Server')
    parser.add_argument('config_file', nargs='?', default='config.json',
                       help='Configuration file path (default: config.json)')
    parser.add_argument('--yaml', nargs='?', default='schema.yaml',
                       help='YAML schema file path (default: schema.yaml)')
    parser.add_argument('--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Override log level from config')
    parser.add_argument('--initdb', action='store_true',
                       help='Initialize database: manage required indexes based on model metadata, then exit')
    parser.add_argument('--resetdb', action='store_true',
                       help='Clear all indexes on database, then exit')
    return parser.parse_args()

# Parse command line arguments
args = parse_args()

LOG_FILE = "app.log"
config = Config.initialize(args.config_file)
is_dev = config.get('environment', 'production') == 'development'
project = config.get('project_name', 'Project Name Here')
my_log_level = (args.log_level or 
               config.get('log_level', 'info' if is_dev else 'warning')).upper()

logging.basicConfig(
    level=my_log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Output to console
        logging.FileHandler(LOG_FILE, mode="a"),  # Write to a log file
    ],
)
logger = logging.getLogger(__name__)

# Add the project root to PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Validate database configuration before creating FastAPI app
db_type: str = config.get('database', '')
db_uri: str = config.get('db_uri', '')
db_name: str = config.get('db_name', '')
validations = Config.validations(False)
print(f"Database validations : get/get-all {validations[0]}.  Unique validation: {validations[1]}")

if (db_uri == '' or db_name == '' or db_type == ''):
    logger.error("Missing required database configuration")
    sys.exit(1)

# Validate database type is supported
supported_types = ["mongodb", "elasticsearch"]
if db_type.lower() not in supported_types:
    logger.error(f"Unsupported database type: {db_type}. Supported types: {supported_types}")
    sys.exit(1)

logger.info(f"Database type {db_type} is supported")

# Handle database management commands before creating FastAPI app
if args.initdb or args.resetdb:
    import asyncio
    
    async def handle_db_command():
        try:
            # Initialize database connection
            db_instance = await DatabaseFactory.initialize(db_type, db_uri, db_name)
            initializer = DatabaseInitializer(db_instance)
            
            if args.initdb:
                logger.info("--initdb flag specified, initializing database schema")
                logger.info("Starting database initialization...")
                await initializer.initialize_database()
                logger.info("Database initialization completed successfully")
            
            elif args.resetdb:
                logger.info("--resetdb flag specified, resetting database indexes")
                logger.info("Starting database reset (indexes only)...")
                await initializer.reset_database_indexes()
                logger.info("Database reset completed successfully")
            
            # Cleanup
            await DatabaseFactory.close()
            logger.info("Database connection closed")
            
        except Exception as e:
            logger.error(f"Failed to execute database command: {str(e)}")
            sys.exit(1)
    
    # Run database command and exit
    asyncio.run(handle_db_command())
    sys.exit(0)

# Create the FastAPI app.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info('Startup event called')
    logger.info(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")
    logger.info(f"Connecting to {db_type} datastore at {db_uri} with db {db_name}")
    
    logger.info(f"Registing routers")
    setup_routers(args.yaml)

    try:
        # Initialize database connection for normal server operation
        db_instance = await DatabaseFactory.initialize(db_type, db_uri, db_name)
        logger.info(f"Connected to {db_type} successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        sys.exit(1)

    yield  # Server runs here

    # Shutdown
    try:
        logger.info("Shutdown event called")
        if DatabaseFactory.is_initialized():
            await DatabaseFactory.close()
            logger.info("Database connection closed")
            logger.info("Database instance closed and cleaned up")
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise

app = FastAPI(
    lifespan=lifespan,
    # Enable automatic slash handling and include both versions in OpenAPI schema
    include_in_schema=True,
    # Disable Starlette's built-in exception middleware so our handlers work
    exception_handlers={}
)

# Store FastAPI's original openapi method before we override it
_original_openapi = app.openapi

# Override OpenAPI to serve generated spec if available
def custom_openapi():
    """Serve generated OpenAPI spec or fallback to auto-generated"""
    import json
    from pathlib import Path
    
    openapi_file = Path("openapi.json")
    if openapi_file.exists():
        try:
            with open(openapi_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load generated OpenAPI spec: {e}")
    
    # Fallback to FastAPI's auto-generated spec
    return _original_openapi()

# Replace FastAPI's openapi method with our custom one
app.openapi = custom_openapi

# Also override the endpoint for direct access
@app.get("/openapi.json", include_in_schema=False)
def get_openapi():
    """Direct endpoint for OpenAPI spec"""
    return custom_openapi()

# Override the /docs endpoint to use our custom OpenAPI spec
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI that uses our detailed OpenAPI spec"""
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
    )

# Add CORS middleware
ui_port = config.get('ui_port', 4200)
server_port = config.get('server_port', 5500)
cors_origins = [
    f"http://localhost:{ui_port}",  # Angular dev server
    f"http://localhost:{server_port}"  # Backend API server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=["*"],
    max_age=3600,             # cache preflight for 1 hour
)

async def handle_exception_with_notifications(
    request: Request, 
    exc: Exception, 
    status_code: int,
    entity: str = '',
    operation: str = '',
    notification_handler = None
) -> JSONResponse:
    """Generic exception handler using notification system"""
    from app.notification import start_notifications, end_notifications
    
    # Extract entity from URL if not provided
    if entity is None:
        path_parts = str(request.url.path).strip('/').split('/')
        entity = path_parts[-1] if len(path_parts) > 1 else "unknown"
    
    # Default operation if not provided
    if operation is None:
        operation = "system"
    
    logger.error(f"Exception in {entity}.{operation}: {exc}")
    notifications = start_notifications(entity=entity, operation=operation)
    
    try:
        # Call the specific notification handler
        if notification_handler:
            notification_handler(exc, entity, operation)
        
        return JSONResponse(
            status_code=status_code,
            content=notifications.to_response(None)
        )
    finally:
        end_notifications()

def handle_database_error_notifications(exc: DatabaseError, entity: str, operation: str):
    """Handle database error notifications"""
    from app.notification import notify_error, NotificationType
    notify_error(exc.message, NotificationType.SYSTEM, entity=entity, operation=operation)

def handle_validation_error_notifications(exc: ValidationError, entity: str, operation: str):
    """Handle validation error notifications"""
    from app.notification import notify_error, NotificationType
    for field_error in exc.invalid_fields:
        notify_error(field_error.message, NotificationType.VALIDATION, 
                    entity=entity, field=field_error.field, value=field_error.value)

def handle_request_validation_error_notifications(exc: RequestValidationError, entity: str, operation: str):
    """Handle FastAPI request validation error notifications"""
    from app.notification import notify_validation_error
    for error in exc.errors():
        field = str(error['loc'][-1]) if error['loc'] else 'unknown'
        message = error['msg']
        value = error.get('input')
        notify_validation_error(f"Invalid {field}: {message}", 
                              field=field, value=value, entity=entity)

def handle_not_found_error_notifications(exc: NotFoundError, entity: str, operation: str):
    """Handle not found error notifications"""
    from app.notification import notify_error, NotificationType
    notify_error(exc.message, NotificationType.BUSINESS, entity=entity)

def handle_duplicate_error_notifications(exc: DuplicateError, entity: str, operation: str):
    """Handle duplicate error notifications"""
    from app.notification import notify_validation_error
    notify_validation_error(exc.message, field=exc.field, value=exc.value, entity=entity)

def handle_generic_error_notifications(exc: Exception, entity: str, operation: str):
    """Handle generic error notifications"""
    from app.notification import notify_error, NotificationType
    notify_error(f"An unexpected error occurred: {str(exc)}", NotificationType.SYSTEM, entity=entity)

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle database errors"""
    return await handle_exception_with_notifications(
        request, exc, 500, exc.entity, exc.operation, handle_database_error_notifications
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors"""
    return await handle_exception_with_notifications(
        request, exc, 422, exc.entity, "validation", handle_validation_error_notifications
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors"""
    return await handle_exception_with_notifications(
        request, exc, 422, operation="request_validation", 
        notification_handler=handle_request_validation_error_notifications
    )

@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    """Handle not found errors"""
    return await handle_exception_with_notifications(
        request, exc, 404, exc.entity, "lookup", handle_not_found_error_notifications
    )

@app.exception_handler(DuplicateError)
async def duplicate_error_handler(request: Request, exc: DuplicateError):
    """Handle duplicate errors"""
    return await handle_exception_with_notifications(
        request, exc, 409, exc.entity, "validation", handle_duplicate_error_notifications
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return await handle_exception_with_notifications(
        request, exc, 500, operation="system", notification_handler=handle_generic_error_notifications)
 
@app.get('')
def read_root():
    return {'message': f'Welcome to the {project} Management System'}

@app.get('/api/metadata')
def get_entities_metadata():
    return  {
        "projectName": project,
        "database": db_type,
        "entities": {
            "Account": Account.get_metadata(),
            "User": User.get_metadata(),
            "Profile": Profile.get_metadata(),
            "TagAffinity": TagAffinity.get_metadata(),
            "Event": Event.get_metadata(),
            "UserEvent": UserEvent.get_metadata(),
            "Url": Url.get_metadata(),
            "Crawl": Crawl.get_metadata(),
        }
    }

def main():
    args = parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger.info("Welcome to the  Management System")
    logger.info(" Access Swagger docs at http://127.0.0.1:5500/docs")

    # Start the server normally if --initdb is not present
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=server_port,
        reload=True,
        reload_dirs=[str(Path(__file__).resolve().parent)]
    )

if __name__ == "__main__":
    main()
