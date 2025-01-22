from pathlib import Path
from bson.objectid import ObjectId
from typing import Dict, Any
import json

# Path to the configuration file
CONFIG_FILE = Path('app/config.json')

def load_config():
    """
    Load and return the configuration from config.json.
    """
    if not CONFIG_FILE.exists():
        print(f'Configuration file not found: {CONFIG_FILE}')
        config = {
            'environment': 'production',
            'host': '127.0.0.1',
            'app_port': 8000,
            "mongo_uri": "mongodb://localhost:27017",
            "db_name": "event_management_system",
            "log_level": "warning",
        }
        return config
    with open(CONFIG_FILE, 'r') as file:
        return json.load(file)

def serialize_mongo_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize MongoDB document for JSON response.
    Convert ObjectId to string.
    """
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['_id'] = str(doc['_id'])
    return doc
