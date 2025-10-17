from pathlib import Path
from typing import Dict, Any, Tuple
import json
from app.utils import load_settings

class Config:
    """Static configuration class - no instances, only class methods"""
    _config: Dict[str, Any] = {}

    @classmethod
    def initialize(cls, config_file: str) -> Dict[str, Any]:
        """Initialize the config with values from config file"""
        cls._config = cls._load_system_config(config_file)
        return cls._config

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a configuration value by key"""
        return cls._config.get(key, default)

    @classmethod
    def get_db_params(cls) -> Tuple[str, str, str]:
        """Get database parameters from config data"""
        return (
            cls._config.get('database', ''),
            cls._config.get('db_uri', ''),
            cls._config.get('db_name', '')
        )

    @classmethod
    def _load_system_config(cls, config_file: str) -> Dict[str, Any]:
        """
        Load and return the configuration from config.json.
        If the file is not found, return default configuration values.
        """
        if len(config_file) > 0:
            config_path = Path(config_file)
            if config_path.exists():
                return load_settings(config_path)
        print(f'Warning: Configuration file "{config_file}" not found. Using defaults.')
        return {
            'server_url' : 'http://localhost:5500',
            'mongo_uri': 'mongodb://localhost:27017',
            'db_name': 'default_db',
            'server_port': 8000,
            'environment': 'production',
            'log_level': 'info',
            'validation': '',
            'case_sensitive': False
        }

    @classmethod
    def validation(cls, get_multiple: bool) -> bool:
        """Get the current validation type from config

        Rules:
        - validation="single|multiple" : validate on single get (get) or multiple gets (get_all, list)
        - Any other value: No validation
        Notes:
        - save validates everything by default
        - get/get_all validates fk only
        - get with view does selective fk validation based on view spec
        """
        validation = cls._config.get('validation', '')

        if validation == 'multiple':
            # multiple setting applies to ALL operations (both single get and get_all)
            return True
        elif validation == 'single' and not get_multiple:
            # single setting applies only to single get operations
            return True
        else:
            # No FK validation
            return False

    @classmethod
    def elasticsearch_strict_consistency(cls) -> bool:
        """Check if Elasticsearch should use strict consistency mode.

        When enabled (default), uses refresh='wait_for' on write operations to ensure
        documents are immediately searchable. This is required for synthetic unique
        constraint validation to work correctly with concurrent requests.

        When disabled, writes are faster but duplicate constraint validation may fail
        under concurrent load (only safe for single-client testing scenarios).

        Returns:
            bool: True if strict consistency is enabled (default), False otherwise
        """
        return cls._config.get('elasticsearch_strict_consistency', True)