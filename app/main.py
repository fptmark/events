from contextlib import asynccontextmanager
import sys
import argparse
from pathlib import Path
from app.config import Config
from app.db import DatabaseFactory
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.services.metadata import MetadataService
from app.services.model import ModelService
from app.exceptions import StopWorkError
from app.routers.router import get_all_dynamic_routers
from app.routers.admin import router as admin_router

from app.services.auth.cookies.redis_provider import CookiesAuth as Auth

ENTITIES = [
   "Account",
   "User",
   "Profile",
   "TagAffinity",
   "Event",
   "UserEvent",
   "Url",
   "Crawl",
]

import logging

def setup_routers(yaml_file: str):
    # --- Dynamic Registration of Routers for Entities --- #
    for router in get_all_dynamic_routers(Path(yaml_file)):
        app.include_router(router, prefix="/api")

    app.include_router(admin_router)

def log_initialization_failure(error_message = None):
    """Log database initialization failure with prominent formatting"""
    RED_BOLD = "\033[1;31m"
    RESET = "\033[0m"

    logger.error("=" * 80)
    if error_message:
        logger.error(f"{RED_BOLD}DATABASE INITIALIZATION FAILED{RESET}")
        logger.error("=" * 80)
        logger.error(f"Error: {error_message}")
    else:
        logger.error(f"{RED_BOLD}DATABASE INITIALIZATION FAILED - INDEXES COULD NOT BE CREATED{RESET}")
        logger.error("=" * 80)
        logger.error("This usually means there is duplicate data violating unique constraints.")
        logger.error("")

async def prompt_and_wipe_database(db_instance) -> bool:
    """Prompt user to wipe database and perform wipe if confirmed.

    Returns:
        bool: True if wipe succeeded, False otherwise
    """
    response = input("Do you want to WIPE ALL DATA and reinitialize the database? (yes/no): ").strip().lower()

    if response == 'yes':
        logger.info("Wiping and reinitializing database...")
        wipe_success = await db_instance.core.wipe_and_reinit()

        if wipe_success:
            logger.info("Database wiped and reinitialized successfully!")
            logger.info("Please restart the application.")
            return True
        else:
            logger.error("Failed to wipe and reinitialize database")
            return False
    else:
        logger.error("=" * 80)
        logger.error("WARNING: The application will terminate.")
        logger.error("         Indexes could not be created and data integrity cannot be guaranteed.")
        logger.error("=" * 80)
        return False

async def initialize_database_indexes(db_instance) -> None:
    """Initialize database indexes with error handling and user prompts.

    Raises:
        SystemExit: If initialization fails and cannot be recovered
    """
    logger.info("Running automatic database initialization...")

    try:
        success = await db_instance.indexes.initialize()

        if not success:
            log_initialization_failure()
            wipe_success = await prompt_and_wipe_database(db_instance)
            sys.exit(0 if wipe_success else 1)
        else:
            logger.info("Automatic database initialization completed successfully")

    except Exception as init_error:
        log_initialization_failure(str(init_error))
        wipe_success = await prompt_and_wipe_database(db_instance)
        sys.exit(0 if wipe_success else 1)

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
get_validation = Config.validation(False)
get_all_validation = Config.validation(True)
print(f"Validations : get={get_validation}.  get_all={get_all_validation}")

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
    ModelService.initialize(ENTITIES)
    logger.info("Metadata & Model services initialized successfully")

    logger.info(f"Registing routers")
    setup_routers(args.yaml)

    try:
        # Initialize database connection for normal server operation
        db_instance = await DatabaseFactory.initialize(db_type, db_uri, db_name)
        logger.info(f"Connected to {db_type} successfully")
                
        # Auto-run database initialization unless --noinitdb flag is set
        if not args.noinitdb:
            await initialize_database_indexes(db_instance)
        else:
            logger.info("Skipping automatic database initialization (--noinitdb flag)")

    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
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

# FORCE LOWERCASE URL MIDDLEWARE - Convert entity names to lowercase BEFORE routing
@app.middleware("http")
async def force_lowercase_url_middleware(request: Request, call_next):
    """Convert entity names in URL path to lowercase before routing"""
    original_path = request.url.path
    
    # Convert path to lowercase for API routes
    if original_path.startswith("/api/"):
        new_path = original_path.lower()
        if new_path != original_path:
            logger.info(f"URL normalization: {original_path} -> {new_path}")
            # Modify the scope directly
            request.scope["path"] = new_path
    
    # Continue with processing
    response = await call_next(request)
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

@app.exception_handler(StopWorkError)
async def stop_work_handler(request: Request, exc: StopWorkError):
    """Handle all stop-work errors with unified response"""
    from app.routers.endpoint_handlers import update_response
    
    logger.error(f"Stop-work error [{exc.error_type}]: {exc.detail}")
    
    # Notification system already populated by notify.py
    # Use update_response to maintain consistent API structure
    response_data = update_response(data=None)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions using consistent response format"""
    from app.routers.endpoint_handlers import update_response
    
    logger.info(f"HTTP {exc.status_code}: {exc.detail}")
    
    # Use update_response to maintain consistent API structure
    response_data = update_response(data=None)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )

# All validation and system errors now handled by StopWorkError via notification system

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