from pathlib import Path
from typing import Dict, Any, Tuple
import json
from app.utils import load_settings

class Config:
    _config: Dict[str, Any] = {}

    def __new__(cls) -> 'Config':
        if not hasattr(cls, '_instance'):
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, config_file: str) -> Dict[str, Any]:
        """Initialize the config singleton with values from config file"""
        cls._config = cls._load_system_config(config_file)
        return cls._config

    @staticmethod
    def get_db_params(config_data: dict) -> Tuple[str, str, str]:
        """Get database parameters from config data"""
        return (
            config_data.get('database', ''),
            config_data.get('db_uri', ''), 
            config_data.get('db_name', '')
        )


    @staticmethod
    def _load_system_config(config_file: str) -> Dict[str, Any]:
        """
        Load and return the configuration from config.json.
        If the file is not found, return default configuration values.
        """
        if len(config_file) > 0:
            config_path = Path(config_file)
            if config_path.exists():
                return load_settings(config_path)
        print(f'Warning: Configuration file \"{config_file}\" not found. Using defaults.')
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

    @staticmethod
    def validation(get_multiple: bool) -> bool:
        """Get the current validation type from config
        
        Rules:
        - validation="single|multiple" : validate on single get (get) or multiple gets (get_all, list)
        - Any other value: No validation
        Notes:
        - save validates everything by default
        - get/get_all validates fk only
        - get with view does selective fk validation based on view spec
        """
        validation = Config._config.get('validation', '')
        
        if validation == 'multiple':
            # multiple setting applies to ALL operations (both single get and get_all)
            return True
        elif validation == 'single' and not get_multiple:
            # single setting applies only to single get operations
            return True
        else:
            # No FK validation
            return False
