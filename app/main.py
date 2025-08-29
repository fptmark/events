from contextlib import asynccontextmanager
import sys
import argparse
from pathlib import Path
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import app.utils as utils
from app.config import Config
from app.db import DatabaseFactory
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.errors import DatabaseError
# Note: ValidationError, NotFoundError, DuplicateError removed - using notification system

from app.routers.router import get_all_dynamic_routers

from app.services.auth.cookies.redis_provider import CookiesAuth as Auth
from app.services.metadata import MetadataService

# from app.models.account_model import Account
# from app.models.user_model import User
# from app.models.profile_model import Profile
# from app.models.tagaffinity_model import TagAffinity
# from app.models.event_model import Event
# from app.models.userevent_model import UserEvent
# from app.models.url_model import Url
# from app.models.crawl_model import Crawl

# Initialize metadata service with entity list
ENTITIES = ['Account', 'User', 'Profile', 'TagAffinity', 'Event', 'UserEvent', 'Url', 'Crawl']

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
    parser.add_argument('--noinitdb', action='store_true',
                           help='Skip automatic database initialization on startup (for large databases)')
  
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
validation = Config.validation(False)
print(f"validation : get = {validation}.")

if (db_uri == '' or db_name == '' or db_type == ''):
    logger.error("Missing required database configuration")
    sys.exit(1)

# Validate database type is supported
supported_types = ["mongodb", "elasticsearch"]
if db_type.lower() not in supported_types:
    logger.error(f"Unsupported database type: {db_type}. Supported types: {supported_types}")
    sys.exit(1)

logger.info(f"Database type {db_type} is supported")

# Create the FastAPI app.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info('Startup event called')
    logger.info(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")
    logger.info(f"Connecting to {db_type} datastore at {db_uri} with db {db_name}")
    
    # Initialize metadata service
    logger.info("Initializing metadata service...")
    MetadataService.initialize(ENTITIES)
    logger.info("Metadata service initialized successfully")
    
    logger.info(f"Registing routers")
    setup_routers(args.yaml)

    try:
        # Initialize database connection for normal server operation
        db_instance = await DatabaseFactory.initialize(db_type, db_uri, db_name)
        logger.info(f"Connected to {db_type} successfully")

                
        # Auto-run database initialization unless --noinitdb flag is set
        if not args.noinitdb:
            logger.info("Running automatic database initialization...")
            try:
                success = await db_instance.indexes.initialize()
                if not success:
                    logger.warning("Database initialization returned failure (continuing anyway)")
                else:
                    logger.info("Automatic database initialization completed successfully")
            except Exception as init_error:
                logger.warning(f"Database initialization failed (continuing anyway): {str(init_error)}")
        else:
            logger.info("Skipping automatic database initialization (--noinitdb flag)")

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

# FORCE LOWERCASE URL MIDDLEWARE - Convert entire URL to lowercase BEFORE any processing
@app.middleware("http")
async def force_lowercase_url_middleware(request: Request, call_next):
    """Convert the entire URL (path + query string) to lowercase before any processing"""
    # Get the original scope
    scope = request.scope
    
    # URL normalization now handled by RequestContext
    
    # Create new request with lowercase URL
    new_request = Request(scope, request.receive)
    
    # Continue with processing
    response = await call_next(new_request)
    return response

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
setattr(app, 'openapi', custom_openapi)

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



@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle database errors"""
    from app.services.notification import Notification, ErrorType
    
    logger.error(f"Database error in {exc.entity}.{exc.operation}: {exc}")
    
    # Add error to notification system (notification collection should already be started by endpoint handler)
    Notification.error(ErrorType.DATABASE, exc.message)
    
    notification_response = Notification.end()
    return JSONResponse(
        status_code=500,
        content={
            "data": None,
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "failed")
        }
    )

# ValidationError handler removed - validation errors now handled by notification system

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors"""
    from app.services.notification import Notification, WarningType
    
    logger.error(f"Request validation error: {exc}")
    
    # Add validation warnings to notification system
    for error in exc.errors():
        field = str(error['loc'][-1]) if error['loc'] else 'unknown'
        message = error['msg']
        Notification.warning(WarningType.VALIDATION, f"Invalid {field}: {message}", field=field)
    
    notification_response = Notification.end()
    return JSONResponse(
        status_code=422,
        content={
            "data": None,
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "failed")
        }
    )

# NotFoundError and DuplicateError handlers removed - these errors now handled by notification system

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    from app.services.notification import Notification, ErrorType
    
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # Add system error to notification system
    Notification.error(ErrorType.SYSTEM, f"An unexpected error occurred: {str(exc)}")
    
    notification_response = Notification.end()
    return JSONResponse(
        status_code=500,
        content={
            "data": None,
            "notifications": notification_response.get("notifications", {}),
            "status": notification_response.get("status", "failed")
        }
    )
 
@app.get('')
def read_root():
    return {'message': f'Welcome to the {project} Management System'}

@app.get('/api/metadata')
def get_entities_metadata():
    entities = {}
    
    for entity in ENTITIES:
        entities[entity] = MetadataService.get(entity)
    
    return {
        "projectName": project,
        "database": db_type,
        "entities": entities
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
