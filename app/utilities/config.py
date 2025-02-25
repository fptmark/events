import json
from pathlib import Path
from bson.objectid import ObjectId
from typing import Dict, Any

# Path to the configuration file
CONFIG_FILE = Path('config.json')

def load_config(config_file: Path = CONFIG_FILE) -> Dict[str, Any]:
    """
    Load and return the configuration from config.json.
    If the file is not found, return default configuration values.
    """
    if not config_file.exists():
        print(f'Warning: Configuration file {config_file} not found. Using defaults.')
        return {
            'mongo_uri': 'mongodb://localhost:27017',
            'db_name': 'default_db',
            'server_port': 8000,
            'environment': 'production',
            'log_level': 'info',
        }
    with open(config_file, 'r') as config_handle:
        return json.load(config_handle)

def serialize_mongo_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize MongoDB document for JSON response.
    Convert ObjectId to string.
    """
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['_id'] = str(doc['_id'])
    return doc
