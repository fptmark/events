from contextlib import asynccontextmanager
import sys
import argparse
from pathlib import Path
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import app.utils as utils
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
    normalize_error_response
)
from app.services.redis_provider import CookiesAuth as Auth

from app.routes.account_router import router as account_router
from app.models.account_model import Account

from app.routes.user_router import router as user_router
from app.models.user_model import User

from app.routes.profile_router import router as profile_router
from app.models.profile_model import Profile

from app.routes.tagaffinity_router import router as tagaffinity_router
from app.models.tagaffinity_model import TagAffinity

from app.routes.event_router import router as event_router
from app.models.event_model import Event

from app.routes.userevent_router import router as userevent_router
from app.models.userevent_model import UserEvent

from app.routes.url_router import router as url_router
from app.models.url_model import Url

from app.routes.crawl_router import router as crawl_router
from app.models.crawl_model import Crawl


import logging

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Events API Server')
    parser.add_argument('config_file', nargs='?', default='config.json',
                       help='Configuration file path (default: config.json)')
    parser.add_argument('--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Override log level from config')
    parser.add_argument('--initdb', action='store_true',
                       help='Initialize database: manage required indexes based on model metadata, then exit')
    return parser.parse_args()

# Parse command line arguments
args = parse_args()

LOG_FILE = "app.log"
config = utils.load_system_config(args.config_file)
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

# Create the FastAPI app.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_type = config.get('database', None)
    db_uri = config.get('db_uri', None)
    db_name = config.get('db_name', None)

    if db_uri and db_name and db_type:
        logger.info('Startup event called')
        logger.info(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")
        logger.info(f"Connecting to {db_type} datastore at {db_uri} with db {db_name}")
        
        try:
            # Create and initialize database instance
            db = DatabaseFactory.create(db_type)
            await db.init(db_uri, db_name)
            DatabaseFactory.set_instance(db, db_type)
            logger.info(f"Connected to {db_type} successfully")

            # Handle --initdb flag if present
            if args.initdb:
                logger.info("--initdb flag specified, initializing database schema")
                logger.info("Starting database initialization...")
                initializer = DatabaseInitializer(db)
                await initializer.initialize_database()
                logger.info("Database initialization completed successfully")
                # Exit after initialization
                sys.exit(0)

        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise RuntimeError(f"Database initialization failed: {str(e)}")
    else:
        logger.error("Missing required database configuration")
        raise RuntimeError("Missing required database configuration")

    yield  # Server runs here

    # Shutdown
    try:
        logger.info("Shutdown event called")
        if DatabaseFactory.is_initialized():
            await DatabaseFactory.close()
            logger.info("Elasticsearch connection closed")
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

app.include_router(account_router, prefix='/api/account', tags=['Account'])
app.include_router(user_router, prefix='/api/user', tags=['User'])
app.include_router(profile_router, prefix='/api/profile', tags=['Profile'])
app.include_router(tagaffinity_router, prefix='/api/tagaffinity', tags=['Tagaffinity'])
app.include_router(event_router, prefix='/api/event', tags=['Event'])
app.include_router(userevent_router, prefix='/api/userevent', tags=['Userevent'])
app.include_router(url_router, prefix='/api/url', tags=['Url'])
app.include_router(crawl_router, prefix='/api/crawl', tags=['Crawl'])

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle database errors"""
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content=normalize_error_response(exc, str(request.url.path))
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content=normalize_error_response(exc, str(request.url.path))
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors"""
    return JSONResponse(
        status_code=422,
        content=normalize_error_response(exc, str(request.url.path))
    )

@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content=normalize_error_response(exc, str(request.url.path))
    )

@app.exception_handler(DuplicateError)
async def duplicate_error_handler(request: Request, exc: DuplicateError):
    return JSONResponse(
        status_code=409,
        content=normalize_error_response(exc, str(request.url.path))
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=normalize_error_response(exc, str(request.url.path))
    )

@app.get('')
def read_root():
    return {'message': f'Welcome to the {project} Management System'}

@app.get('/api/metadata')
def get_entities_metadata():
    return  {
        "projectName": project,
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
    config = utils.load_system_config(args.config_file)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger.info("Welcome to the  Management System")
    logger.info(" Access Swagger docs at http://127.0.0.1:5500/docs")

    # If --initdb flag is present, just initialize the database and exit
    if args.initdb:
        import asyncio
        async def init_db():
            db_type = config.get('database', None)
            db_uri = config.get('db_uri', None)
            db_name = config.get('db_name', None)

            if not all([db_type, db_uri, db_name]):
                logger.error("Missing required database configuration")
                return

            try:
                # Create and initialize database instance
                db = DatabaseFactory.create(db_type)
                await db.init(db_uri, db_name)
                DatabaseFactory.set_instance(db, db_type)
                logger.info(f"Connected to {db_type} successfully")

                # Initialize database schema
                logger.info("--initdb flag specified, initializing database schema")
                logger.info("Starting database initialization...")
                initializer = DatabaseInitializer(db)
                await initializer.initialize_database()
                logger.info("Database initialization completed successfully")

                # Cleanup
                await DatabaseFactory.close()
                logger.info(f"{db_type} connection closed")
                logger.info("Database instance closed and cleaned up")
                logger.info("Database connections closed")

            except Exception as e:
                logger.error(f"Database error: {str(e)}")
                raise

        # Run database initialization
        asyncio.run(init_db())
        return

    # Start the server normally if --initdb is not present
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=5500,
        reload=True,
        reload_dirs=[str(Path(__file__).resolve().parent)]
    )

if __name__ == "__main__":
    main()
