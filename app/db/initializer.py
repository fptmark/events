import logging
from typing import Dict, List, Set, Any
import importlib
import pkgutil
from pathlib import Path

from .base import DatabaseInterface
from .index_manager import IndexManager
from ..errors import DatabaseError


class DatabaseInitializer:
    """
    Database initialization utility that manages collections/indexes
    based on model metadata.
    """
    
    def __init__(self, db: DatabaseInterface):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.index_manager = IndexManager(db)
    
    async def initialize_database(self) -> None:
        """
        Initialize database by:
        1. Discovering required collections and their indexes from model metadata
        2. Managing indexes within each collection
        
        Note: This initialization is non-destructive - it only manages indexes,
        it never removes or creates collections.
        """
        self.logger.info("Starting database initialization...")
        
        try:
            # Discover required collections and indexes from models
            required_structure = await self._discover_required_structure()
            self.logger.info(f"Found {len(required_structure)} collections with index requirements")
            
            # Use IndexManager to handle all index management
            await self.index_manager.initialize_indexes(required_structure)
            
            self.logger.info("Database initialization completed successfully")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise DatabaseError(
                message=f"Failed to initialize database: {str(e)}",
                entity="database",
                operation="initialize"
            )
    
    async def _discover_required_structure(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover required collections and their indexes by examining model metadata.
        
        Returns:
            Dict mapping collection names to their required indexes
        """
        collections_structure = {}
        
        # Import models module to discover all models
        try:
            models_module = importlib.import_module('app.models')
            models_path = Path(models_module.__file__ or "").parent
            
            # Iterate through all Python files in models directory
            for finder, name, ispkg in pkgutil.iter_modules([str(models_path)]):
                if name.endswith('_model'):
                    try:
                        # Import the model module
                        module = importlib.import_module(f'app.models.{name}')
                        
                        # Look for classes with _metadata attribute
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if hasattr(attr, '_metadata') and isinstance(attr._metadata, dict):
                                # Get collection name from Settings.name
                                collection_name = None
                                if hasattr(attr, 'Settings') and hasattr(attr.Settings, 'name'):
                                    collection_name = attr.Settings.name
                                else:
                                    # Skip if no collection name found
                                    continue
                                
                                if collection_name:
                                    # Extract unique constraints from metadata
                                    unique_constraints = attr._metadata.get('uniques', [])
                                    required_indexes = []
                                    
                                    # Add unique constraint indexes
                                    for constraint_fields in unique_constraints:
                                        if isinstance(constraint_fields, list) and constraint_fields:
                                            index_name = f"unique_{'_'.join(constraint_fields)}"
                                            required_indexes.append({
                                                'name': index_name,
                                                'fields': constraint_fields,
                                                'unique': True
                                            })
                                    
                                    collections_structure[collection_name] = required_indexes
                                    self.logger.debug(f"Found model {attr_name} -> collection '{collection_name}' with {len(required_indexes)} unique indexes")
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to import model {name}: {str(e)}")
                        continue
        
        except Exception as e:
            self.logger.error(f"Failed to discover models: {str(e)}")
            raise
        
        return collections_structure
    
    async def reset_database_indexes(self) -> None:
        """
        Reset database indexes by:
        1. Discovering existing collections and their indexes
        2. Deleting all non-system indexes (preserving data)
        
        Note: This only removes indexes, never collections or data.
        """
        self.logger.info("Starting database index reset...")
        
        try:
            # Get list of all collections
            collections = await self.db.list_collections()
            self.logger.info(f"Found {len(collections)} collections to reset indexes for")
            
            # Use IndexManager to handle index reset
            await self.index_manager.reset_indexes(collections)
            
            self.logger.info("Database index reset completed successfully")
            
        except Exception as e:
            self.logger.error(f"Database index reset failed: {str(e)}")
            raise DatabaseError(
                message=f"Failed to reset database indexes: {str(e)}",
                entity="database",
                operation="reset_indexes"
            )