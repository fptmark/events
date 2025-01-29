import sys
from pathlib import Path
from app.utils.config import load_config 
from app.utils.db import Database

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

app = FastAPI()

@app.on_event('startup')
async def startup_event():
    logger.info('Startup event called')
    logger.info(f"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode")
    await Database.init(config['mongo_uri'], config['db_name']) 

# Include routers

@app.get('/')
def read_root():
    return {'message': 'Welcome to the Event Management System'}

if __name__ == '__main__':
    import uvicorn

    logger.info("Welcome to the Event Management System")   

    # Load configuration
    my_host = config.get('host', '0.0.0.0')
    my_port = config.get('app_port', 8000)

    logger.info(f' Access Swagger docs at http://{my_host}:{my_port}/docs') 

    # Run Uvicorn
    uvicorn.run(
        'app.main:app',  # Use the import string for proper reload behavior
        host=my_host,
        port=my_port,
        reload=is_dev,  # Enable reload only in development mode
        reload_dirs=['app'] if is_dev else None,
        log_level=my_log_level.lower(), 
    )

