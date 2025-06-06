import json
from pathlib import Path
from bson.objectid import ObjectId
from typing import Dict, Any, Optional, TypeVar, Type
from pydantic import BaseModel
from beanie import Document
import logging
from datetime import datetime, timezone


# Path to the configuration file
CONFIG_FILE = 'config.json'

T = TypeVar('T')

def load_system_config(config_file: str = CONFIG_FILE) -> Dict[str, Any]:
    """
    Load and return the configuration from config.json.
    If the file is not found, return default configuration values.
    """
    config_path = Path(config_file)
    if not config_path.exists():
        print(f'Warning: Configuration file {config_file} not found. Using defaults.')
        return {
            'mongo_uri': 'mongodb://localhost:27017',
            'db_name': 'default_db',
            'server_port': 8000,
            'environment': 'production',
            'log_level': 'info',
        }
    return load_settings(config_path)


def load_settings(config_file: Path | None) -> Dict[str, Any]:
    try:
        if config_file:
            with open(config_file, 'r') as config_handle:
                return json.load(config_handle)
    except:
        return {}

    return {}


# def serialize_mongo_document(doc: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Serialize MongoDB document for JSON response.
#     Convert ObjectId to string.
#     """
#     if '_id' in doc and isinstance(doc['_id'], ObjectId):
#         doc['_id'] = str(doc['_id'])
#     return doc


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

def get_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Get metadata for a model with proper type hints"""
    overrides = load_settings(Path('overrides.json')) or {}
    name = metadata.get('entity', '')
    entity_cfg = overrides.get(name)
    if entity_cfg:
        deep_merge_dicts(metadata, entity_cfg)
    return metadata



# Helpers for routes

# async def apply_and_save(
#     doc: Document,
#     payload: BaseModel,
#     *,
#     exclude_unset: bool = True
# ) -> Document:
#     """
#     Copy payload fields onto doc and call save().
#     """
#     data = payload.dict(exclude_unset=exclude_unset)
#     for field, value in data.items():
#         setattr(doc, field, value)
#     try:
#         await doc.save()
#     except Exception as e:
#         logging.exception("Error in apply_and_save()")
#         raise
#     return doc

# class DatabaseError(Exception):
#     """Base class for all database-related errors"""
#     def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
#         self.message = message
#         self.details = details or {}
#         super().__init__(message)

# class ValidationError(DatabaseError):
#     """Error for validation failures during database operations"""
#     def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
#         details = {"field": field, "value": value} if field else {}
#         super().__init__(message, details)

def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format a datetime object to ISO format"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()

def parse_datetime(dt_str: str) -> datetime:
    """Parse an ISO format datetime string"""
    return datetime.fromisoformat(dt_str)

def validate_id(id: str) -> bool:
    """Validate if a string is a valid ID format"""
    return bool(id and isinstance(id, str) and len(id) > 0)

def sanitize_field_name(field: str) -> str:
    """Sanitize a field name for database operations"""
    return field.strip().replace('.', '_')
