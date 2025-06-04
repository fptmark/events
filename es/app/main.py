import sys
from pathlib import Path
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import app.utils as utils
from app.db import Database
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from errors import (
    DatabaseError, 
    ValidationError, 
    NotFoundError, 
    DuplicateError, 
    ValidationFailure
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
LOG_FILE = "app.log"
config = utils.load_system_config('config.json' if len(sys.argv) < 2 else sys.argv[1])
is_dev = config.get('environment', 'production') == 'development'
my_log_level = config.get('log_level', 'info' if is_dev else 'warning').upper()

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
    include_in_schema=True
)

# Add CORS middleware
angular = config.get('angular-ui-url', 'http://localhost:4200')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[angular],
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

@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url}")
    resp = await call_next(request)
    logger.info(f"← {resp.status_code} {request.method} {request.url}")
    return resp

@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """Handle database errors"""
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "message": str(exc),
                "error_type": "database_error",
                "context": {"error": str(exc)}
            }
        }
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={
            "detail": {
                "message": str(exc),
                "error_type": "validation_error",
                "entity": exc.entity,
                "invalid_fields": [
                    {
                        "field": f.field,
                        "message": f.message,
                        "value": f.value
                    } for f in exc.invalid_fields
                ]
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors"""
    failures = []
    for err in exc.errors():
        field = err["loc"][-1] if err["loc"] else "unknown"
        failures.append(ValidationFailure(
            field=field,
            message=err["msg"],
            value=err.get("input")
        ))
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "message": "Invalid request data",
                "error_type": "validation_error",
                "entity": request.url.path.split("/")[-1],  # Extract entity from URL
                "invalid_fields": [
                    {
                        "field": f.field,
                        "message": f.message,
                        "value": f.value
                    } for f in failures
                ]
            }
        }
    )

@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content=exc.to_dict()
    )

@app.exception_handler(DuplicateError)
async def duplicate_error_handler(request: Request, exc: DuplicateError):
    return JSONResponse(
        status_code=409,
        content=exc.to_dict()
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": {
                "message": "An unexpected error occurred",
                "error_type": "internal_server_error",
                "context": {
                    "error": str(exc)
                }
            }
        }
    )

@app.on_event('startup')
async def startup_event():
    logger.info('Startup event called')
    logger.info(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")

    db_uri = config.get('db_uri', None)
    db_name = config.get('db_name', None)
    if db_uri and db_name:
        logger.info(f"Connecting to datastore at {db_uri} with db {db_name}")
        await Database.init(db_uri, db_name)
        logger.info(f"Connected...")
        # Initialize the auth service from the hard-coded import.  Need to init all services here
        print(f'>>> Initializing service auth.cookies.redis')
        await Auth.initialize(config['auth.cookies.redis'])
    else:
        logger.error("No db_uri or db_name provided in config.json. Exiting.")
        sys.exit(1)

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