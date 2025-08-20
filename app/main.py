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
    DuplicateError 
)
from app.notification import start_notifications, end_notifications

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

                
        # Auto-run database initialization unless --noinitdb flag is set
        if not args.noinitdb:
            logger.info("Running automatic database initialization...")
            initializer = DatabaseInitializer(db_instance)
            try:
                await initializer.initialize_database()
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
    
    # Convert path to lowercase 
    scope["path"] = scope["path"].lower()
    
    # Convert query string to lowercase
    if scope.get("query_string"):
        original_query = scope["query_string"].decode('utf-8')
        lowercase_query = original_query.lower()
        scope["query_string"] = lowercase_query.encode('utf-8')
    
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
    from app.notification import end_notifications, notify_database_error
    
    logger.error(f"Database error in {exc.entity}.{exc.operation}: {exc}")
    
    # Add notification to existing collection (started by endpoint handler)
    notify_database_error(exc.message, entity=exc.entity)
    
    collection = end_notifications()
    enhanced_response = collection.to_entity_grouped_response(data=None, is_bulk=False)
    return JSONResponse(
        status_code=500,
        content=enhanced_response
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors"""
    from app.notification import end_notifications
    
    logger.error(f"Validation error in {exc.entity}: {exc}")
    
    # Notifications already sent directly by validation functions before raising ValidationError
    # Just collect the existing notifications and format response
    collection = end_notifications()
    enhanced_response = collection.to_entity_grouped_response(data=None, is_bulk=False)
    return JSONResponse(
        status_code=422,
        content=enhanced_response
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors"""
    from app.notification import end_notifications, notify_validation_error, get_notifications
    
    logger.error(f"Request validation error: {exc}")
    
    # Add notifications to existing collection (started by endpoint handler)
    for error in exc.errors():
        field = str(error['loc'][-1]) if error['loc'] else 'unknown'
        message = error['msg']
        notify_validation_error(f"Invalid {field}: {message}", 
                              field_name=field)
    
    collection = end_notifications()
    enhanced_response = collection.to_entity_grouped_response(data=None, is_bulk=False)
    return JSONResponse(
        status_code=422,
        content=enhanced_response
    )

@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    """Handle not found errors"""
    from app.notification import end_notifications, notify_business_error
    
    logger.error(f"Not found error in {exc.entity}: {exc}")
    
    # Add notification to existing collection (started by endpoint handler)
    notify_business_error(exc.message, entity=exc.entity)
    
    collection = end_notifications()
    enhanced_response = collection.to_entity_grouped_response(data=None, is_bulk=False)
    return JSONResponse(
        status_code=404,
        content=enhanced_response
    )

@app.exception_handler(DuplicateError)
async def duplicate_error_handler(request: Request, exc: DuplicateError):
    """Handle duplicate errors"""
    from app.notification import end_notifications, notify_business_error
    
    logger.error(f"Duplicate error in {exc.entity}: {exc}")
    
    # Add notification to existing collection (started by endpoint handler)
    # Duplicate errors are business errors, not validation errors
    notify_business_error(exc.message, field_name=exc.field, entity=exc.entity)
    
    collection = end_notifications()
    enhanced_response = collection.to_entity_grouped_response(data=None, is_bulk=False)
    return JSONResponse(
        status_code=409,
        content=enhanced_response
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    from app.notification import end_notifications, notify_system_error
    
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # Add notification to existing collection (started by endpoint handler)
    notify_system_error(f"An unexpected error occurred: {str(exc)}")
    
    collection = end_notifications()
    enhanced_response = collection.to_entity_grouped_response(data=None, is_bulk=False)
    return JSONResponse(
        status_code=500,
        content=enhanced_response
    )
 
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
