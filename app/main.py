from fastapi import FastAPI
from app.utils.db import init_db
import json
from pathlib import Path

# Path to the configuration file
CONFIG_FILE = Path('app/config.json')

def load_config():
    """
    Load and return the configuration from config.json.
    """
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f'Configuration file not found: {CONFIG_FILE}')
    with open(CONFIG_FILE, 'r') as file:
        return json.load(file)

from app.routes.account_routes import router as account_router
from app.routes.user_routes import router as user_router
from app.routes.profile_routes import router as profile_router
from app.routes.tagaffinity_routes import router as tagaffinity_router
from app.routes.event_routes import router as event_router
from app.routes.userevent_routes import router as userevent_router
from app.routes.url_routes import router as url_router
from app.routes.crawl_routes import router as crawl_router

app = FastAPI()

@app.on_event('startup')
async def startup_event():
    await init_db()  # Initialize MongoDB connection

# Include routers
app.include_router(account_router, prefix='/account', tags=['Account'])
app.include_router(user_router, prefix='/user', tags=['User'])
app.include_router(profile_router, prefix='/profile', tags=['Profile'])
app.include_router(tagaffinity_router, prefix='/tagaffinity', tags=['TagAffinity'])
app.include_router(event_router, prefix='/event', tags=['Event'])
app.include_router(userevent_router, prefix='/userevent', tags=['UserEvent'])
app.include_router(url_router, prefix='/url', tags=['URL'])
app.include_router(crawl_router, prefix='/crawl', tags=['Crawl'])

@app.get('/')
def read_root():
    return {'message': 'Welcome to the Event Management System'}

if __name__ == '__main__':
    import uvicorn
    try:
        config = load_config()
    except FileNotFoundError:
        config = {
            'host': '0.0.0.0',
            'app_port': 8000,
            'reload_dirs': ['app'],
        }
    uvicorn.run(
        app,
        host=config.get('host', '0.0.0.0'),
        port=config.get('app_port', 8000),
        reload=True,
        reload_dirs=config.get('reload_dirs', ['app']),
    )
