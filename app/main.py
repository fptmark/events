import sys
from pathlib import Path

# Add the project root to PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from app.utils.db import init_db
from app.utils.helpers import load_config


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
    print('Startup event called')
    config = load_config()
    print(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")
    await init_db()

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

    # Load configuration
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f'Error loading configuration: {e}')
        config = {
            'environment': 'production',
            'host': '0.0.0.0',
            'app_port': 8000,
        }

    # Determine runtime mode
    is_dev = config.get('environment', 'production') == 'development'

    # Run Uvicorn
    uvicorn.run(
        'app.main:app',  # Use the import string for proper reload behavior
        host=config.get('host', '0.0.0.0'),
        port=config.get('app_port', 8000),
        reload=is_dev,  # Enable reload only in development mode
        reload_dirs=['app'] if is_dev else None,
        log_level='debug' if is_dev else 'info',
    )
