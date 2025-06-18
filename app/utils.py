import json
from pathlib import Path
from bson.objectid import ObjectId
from typing import Dict, Any, Optional, TypeVar, Type
from pydantic import BaseModel
from beanie import Document
import logging
from datetime import datetime, timezone
import re


# Path to the configuration file

T = TypeVar('T')

def load_settings(config_file: Path | None) -> Dict[str, Any]:
    try:
        if config_file:
            with open(config_file, 'r') as config_handle:
                return json.load(config_handle)
    except:
        return {}

    return {}


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

def parse_currency(value):
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return value
    
    # Remove $, commas, parentheses, whitespace
    cleaned = re.sub(r'[$,\s()]', '', str(value))
    
    # Handle negative in parentheses
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = f'-{cleaned[1:-1]}'
    
    try:
        return float(cleaned)
    except ValueError:
        return None

def get_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Get metadata for a model with proper type hints"""
    overrides = load_settings(Path('overrides.json')) or {}
    name = metadata.get('entity', '')
    entity_cfg = overrides.get(name)
    if entity_cfg:
        deep_merge_dicts(metadata, entity_cfg)
    return metadata


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
