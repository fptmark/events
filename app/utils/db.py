from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.utils.helpers import load_config

from app.models.account_model import Account
from app.models.user_model import User
from app.models.profile_model import Profile
from app.models.tagaffinity_model import TagAffinity
from app.models.event_model import Event
from app.models.userevent_model import UserEvent
from app.models.url_model import URL
from app.models.crawl_model import Crawl

# MongoDB connection string
client = None

async def init_db():
    """
    Initialize MongoDB connection and Beanie models.
    """
    global client
    config = load_config()
    client = AsyncIOMotorClient(config['mongo_uri'])
    db = client[config['db_name']]

    # Initialize Beanie models
    await init_beanie(database=db, document_models=[Account, User, Profile, TagAffinity, Event, UserEvent, URL, Crawl])

def get_db():
    """
    Get a direct connection to the MongoDB database.
    """
    if client is None:
        raise Exception("Database client is not initialized. Call init_db() first.")
    config = load_config()
    return client[config['db_name']]
