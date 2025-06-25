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
    def _load_system_config(config_file: str) -> Dict[str, Any]:
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
                'get-validation': 'default'
            }
        return load_settings(config_path)

    # @staticmethod
    # def validation_type() -> str:
    #     """Get the current validation type from config"""
    #     return Config._config.get('get_validation', 'default')

    # @staticmethod
    # def unique_validation() -> bool:
    #     """Get the current validation type from config"""
    #     return Config._config.get('unique_validation', False)

    @staticmethod
    def validations(get_all: bool) -> Tuple[bool, bool]:
        """Get the current validation type from config"""
        get_validation = False
        validation = Config._config.get('get_validation', '') 
        if get_all and validation == 'get_all':
            get_validation = True
        else:
            get_validation = validation in ['get', 'get_all'] #

        unique_validation = Config._config.get('unique_validation', False)
        return (get_validation, unique_validation)

    # @staticmethod
    # def is_get_validation(get_all: bool) -> bool:
    #     """Check if validation should occur for get operations"""
    #     if get_all and Config.validation_type() == 'get-all':
    #         return True
    #     else:
    #          return Config.validation_type() in ['get', 'get-all']

