import sys
import argparse
from pathlib import Path
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import app.utils as utils
from app.db import DatabaseFactory
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from errors import (
    DatabaseError, 
    ValidationError, 
    NotFoundError, 
    DuplicateError, 
    ValidationFailure,
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
    parser.add_argument('--db-type', default='elasticsearch', 
                       choices=['elasticsearch', 'mongodb'],
                       help='Database backend to use (default: elasticsearch)')
    parser.add_argument('--log-level', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Override log level from config')
    return parser.parse_args()

# Parse command line arguments
args = parse_args()

LOG_FILE = "app.log"
config = utils.load_system_config(args.config_file)
is_dev = config.get('environment', 'production') == 'development'
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
app = FastAPI(
    # Enable automatic slash handling and include both versions in OpenAPI schema
    include_in_schema=True,
    # Disable Starlette's built-in exception middleware so our handlers work
    exception_handlers={}
)

# Add CORS middleware
server_port = config.get('server_port', 5500)
cors_origins = [
    f"http://localhost:4200",  # Angular dev server
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

# Mount all routers with their prefixes and tags
app.include_router(account_router, prefix='/api/account', tags=['Account'])
app.include_router(user_router, prefix='/api/user', tags=['User'])
app.include_router(profile_router, prefix='/api/profile', tags=['Profile'])
app.include_router(tagaffinity_router, prefix='/api/tagaffinity', tags=['TagAffinity'])
app.include_router(event_router, prefix='/api/event', tags=['Event'])
app.include_router(userevent_router, prefix='/api/userevent', tags=['UserEvent'])
app.include_router(url_router, prefix='/api/url', tags=['Url'])
app.include_router(crawl_router, prefix='/api/crawl', tags=['Crawl'])

# Removed logging middleware - it was interfering with exception handling
# @app.middleware("http") 
# async def log_all_requests(request: Request, call_next):
#     logger.info(f"→ {request.method} {request.url}")
#     resp = await call_next(request)
#     logger.info(f"← {resp.status_code} {request.method} {request.url}")
#     return resp

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

@app.on_event('startup')
async def startup_event():
    logger.info('Startup event called')
    logger.info(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")
    logger.info(f"Database backend: {args.db_type}")

    db_uri = config.get('db_uri', None)
    db_name = config.get('db_name', None)
    if db_uri and db_name:
        logger.info(f"Connecting to {args.db_type} datastore at {db_uri} with db {db_name}")
        
        # Create and initialize database instance
        try:
            db = DatabaseFactory.create(args.db_type)
            await db.init(db_uri, db_name)
            DatabaseFactory.set_instance(db, args.db_type)
            logger.info(f"Connected to {args.db_type} successfully")
        except Exception as e:
            logger.error(f"Failed to initialize {args.db_type} database: {str(e)}")
            sys.exit(1)
        
        # Initialize the auth service from the hard-coded import.  Need to init all services here
        print(f'>>> Initializing service auth.cookies.redis')
        await Auth.initialize(config['auth.cookies.redis'])
    else:
        logger.error("No db_uri or db_name provided in config.json. Exiting.")
        sys.exit(1)

@app.on_event('shutdown')
async def shutdown_event():
    """Clean up database connections on shutdown"""
    logger.info('Shutdown event called')
    await DatabaseFactory.close()
    logger.info('Database connections closed')

@app.get('')
def read_root():
    return {'message': 'Welcome to the Event Management System'}

@app.get('/api/metadata')
def get_entities_metadata():
    return  {
        "projectName": "Events",
        "entities": [
            Account.get_metadata(),     
            User.get_metadata(),     
            Profile.get_metadata(),     
            TagAffinity.get_metadata(),     
            Event.get_metadata(),     
            UserEvent.get_metadata(),     
            Url.get_metadata(),     
            Crawl.get_metadata(),     
        ]
    }

if __name__ == '__main__':
    import uvicorn
    logger.info("Welcome to the Event Management System")
    my_host = config.get('host', '0.0.0.0')
    my_port = config.get('server_port', 8000)
    logger.info(f' Access Swagger docs at http://{my_host}:{my_port}/docs')
    uvicorn.run(
        'app.main:app',
        host=my_host,
        port=my_port,
        reload=is_dev,
        reload_dirs=['app'] if is_dev else None,
        log_level=my_log_level.lower(),
        proxy_headers=True,
        forwarded_allow_ips='*'
    )