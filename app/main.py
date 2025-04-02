import copy
import sys
from pathlib import Path
from app.utilities.config import load_config 
from app.db import Database

from app.services.auth.cookies.redis import CookiesAuth as Auth

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
config = load_config()
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

from fastapi import FastAPI

# Create the FastAPI app.
app = FastAPI()

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware

angular = config.get('angular-ui-url', 'http://localhost:4200')
app.add_middleware(
    CORSMiddleware,
    allow_origins=[angular],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event('startup')
async def startup_event():
    logger.info('Startup event called')
    logger.info(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")
    await Database.init(config['mongo_uri'], config['db_name']) 
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

@app.get('/api/entities')
def get_entities_metadata():
    result = [
        Account.get_metadata(),     
        User.get_metadata(),     
        Profile.get_metadata(),     
        TagAffinity.get_metadata(),     
        Event.get_metadata(),     
        UserEvent.get_metadata(),     
        Url.get_metadata(),     
        Crawl.get_metadata(),     
    ]

    r1 = copy.deepcopy(result)
    for r in r1:
        r.pop('fields')
    return r1

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