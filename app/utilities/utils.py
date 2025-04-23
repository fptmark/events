import json
from pathlib import Path
from bson.objectid import ObjectId
from typing import Dict, Any
from pydantic import BaseModel
from beanie import Document
import logging


# Path to the configuration file
CONFIG_FILE = Path('config.json')

def load_system_config(config_file: Path = CONFIG_FILE) -> Dict[str, Any]:
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
    return load_settings(config_file)


def load_settings(config_file: Path | None) -> Dict[str, Any]:
    try:
        if config_file:
            with open(config_file, 'r') as config_handle:
                return json.load(config_handle)
    except:
        return {}

    return {}


def serialize_mongo_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Serialize MongoDB document for JSON response.
    Convert ObjectId to string.
    """
    if '_id' in doc and isinstance(doc['_id'], ObjectId):
        doc['_id'] = str(doc['_id'])
    return doc


# Helper for models

def deep_merge_dicts(dest, override):
    for key, value in override.items():
        if (
            key in dest
            and isinstance(dest[key], dict)
            and isinstance(value, dict)
        ):
            deep_merge_dicts(dest[key], value)
        else:
            dest[key] = value

def get_metadata(metadata) -> Dict[str, Any]:
    overrides = load_settings(Path('overrides.json')) or {}
    name = metadata.get('entity', '')
    entity_cfg = overrides.get(name)
    if entity_cfg:
        deep_merge_dicts(metadata, entity_cfg)
    return metadata



# Helpers for routes

async def apply_and_save(
    doc: Document,
    payload: BaseModel,
    *,
    exclude_unset: bool = True
) -> Document:
    """
    Copy payload fields onto doc and call save().
    """
    data = payload.dict(exclude_unset=exclude_unset)
    for field, value in data.items():
        setattr(doc, field, value)
    try:
        await doc.save()
    except Exception as e:
        logging.exception("Error in apply_and_save()")
        raise
    return doc
