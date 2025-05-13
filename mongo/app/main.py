import sys
from pathlib import Path
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
import app.utils as utils
from app.db import Database

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
config = utils.load_system_config('config.json' if len(sys.argv) < 3 else sys.argv[2])
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

from fastapi import FastAPI, Request

# Create the FastAPI app.
app = FastAPI()

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware

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
    max_age=3600,             # cache preflight for 1 hour
)

@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    logger.info(f"→ {request.method} {request.url}")
    resp = await call_next(request)
    logger.info(f"← {resp.status_code} {request.method} {request.url}")
    return resp

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Just log the errors (you can pull out loc/msg/type here if you want)
    for err in exc.errors():
        field = err["loc"][-1]
        logger.error(f"Validation failed on field `{field}`: {err['msg']}")
    # Delegate to FastAPI’s built‑in handler (it will read the body correctly)
    return await request_validation_exception_handler(request, exc)

@app.on_event('startup')
async def startup_event():
    logger.info('Startup event called')
    logger.info(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")

    backend = sys.argv[1] if len(sys.argv) > 1 else config.get('backend', 'mongo')
    uri = config.get(backend + '_uri', '')
    db = config.get('db_name', '')
    logger.info(f"Connecting to {backend} at {uri} with db {db}")
    await Database.init(uri, db)
    logger.info(f"Connected to {backend}")

    # Initialize the auth service from the hard-coded import.
    print(f'>>> Initializing service auth.cookies.redis')
    await Auth.initialize(config['auth.cookies.redis'])

app.include_router(account_router, prefix='/api/account', tags=['Account'])
app.include_router(user_router, prefix='/api/user', tags=['User'])
app.include_router(profile_router, prefix='/api/profile', tags=['Profile'])
app.include_router(tagaffinity_router, prefix='/api/tagaffinity', tags=['Tagaffinity'])
app.include_router(event_router, prefix='/api/event', tags=['Event'])
app.include_router(userevent_router, prefix='/api/userevent', tags=['Userevent'])
app.include_router(url_router, prefix='/api/url', tags=['Url'])
app.include_router(crawl_router, prefix='/api/crawl', tags=['Crawl'])

@app.get('/')
def read_root():
    return {'message': 'Welcome to the Event Management System'}

@app.get('/api/metadata')
def get_entities_metadata():
    return  [
        Account.get_metadata(),     
        User.get_metadata(),     
        Profile.get_metadata(),     
        TagAffinity.get_metadata(),     
        Event.get_metadata(),     
        UserEvent.get_metadata(),     
        Url.get_metadata(),     
        Crawl.get_metadata(),     
    ]

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
    )