import logging
from typing import Dict, List, Set, Any
import importlib
import pkgutil
from pathlib import Path

from .base import DatabaseInterface
from ..errors import DatabaseError


class DatabaseInitializer:
    """
    Database initialization utility that manages collections/indexes
    based on model metadata.
    """
    
    def __init__(self, db: DatabaseInterface):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
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
            
            # Manage indexes for each collection
            self.logger.info("Managing indexes for collections...")
            for collection, required_indexes in required_structure.items():
                await self._manage_collection_indexes(collection, required_indexes)
            
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
    
    async def _manage_collection_indexes(self, collection: str, required_indexes: List[Dict[str, Any]]) -> None:
        """
        Manage indexes for a specific collection.
        
        Args:
            collection: Collection name
            required_indexes: List of required index definitions
        """
        self.logger.info(f"\n--- Managing indexes for collection '{collection}' ---")
        
        if not required_indexes:
            self.logger.info(f"  No indexes required for '{collection}'")
            return
        
        # List required indexes
        self.logger.info(f"  Required indexes for '{collection}':")
        for idx in required_indexes:
            fields = idx.get('fields', [])
            fields_str = " + ".join(fields) if len(fields) > 1 else (fields[0] if fields else 'unknown')
            unique_str = " (UNIQUE)" if idx.get('unique') else ""
            self.logger.info(f"    - {idx.get('name', 'unnamed')}: {fields_str}{unique_str}")
        
        try:
            # Create collection if it doesn't exist
            if not await self.db.collection_exists(collection):
                self.logger.info(f"  Creating collection '{collection}'")
                await self.db.create_collection(collection)
            
            # Get existing indexes
            try:
                existing_indexes = await self.db.list_indexes(collection)
                self.logger.info(f"  Existing indexes for '{collection}':")
                if existing_indexes:
                    for idx in existing_indexes:
                        fields = idx.get('fields', [])
                        fields_str = " + ".join(fields) if len(fields) > 1 else (fields[0] if fields else 'unknown')
                        unique_str = " (UNIQUE)" if idx.get('unique') else ""
                        system_str = " (SYSTEM)" if idx.get('system') else ""
                        self.logger.info(f"    - {idx.get('name', 'unnamed')}: {fields_str}{unique_str}{system_str}")
                else:
                    self.logger.info(f"    - No existing indexes found")
            except Exception as e:
                self.logger.warning(f"  Could not list existing indexes for '{collection}': {str(e)}")
                existing_indexes = []
            
            # Create missing indexes
            existing_index_names = {idx['name'] for idx in existing_indexes}
            for required_idx in required_indexes:
                if required_idx['name'] not in existing_index_names:
                    try:
                        created = await self.db.create_index(
                            collection, 
                            required_idx['fields'], 
                            unique=required_idx['unique']
                        )
                        if created:
                            fields_str = " + ".join(required_idx['fields'])
                            self.logger.info(f"  ✓ Created index '{required_idx['name']}' on {fields_str}")
                        else:
                            self.logger.info(f"  ⚠ Index '{required_idx['name']}' already exists or couldn't be created")
                    except Exception as e:
                        self.logger.error(f"  ✗ Failed to create index '{required_idx['name']}': {str(e)}")
                else:
                    self.logger.info(f"  ✓ Index '{required_idx['name']}' already exists")
            
            # Note: We don't delete unused indexes automatically as they might be manually created
            # and serve other purposes beyond what's defined in model metadata
            
        except Exception as e:
            self.logger.error(f"Failed to manage indexes for collection '{collection}': {str(e)}")
            raise