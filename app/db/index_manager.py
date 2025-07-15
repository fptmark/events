import logging
from typing import Dict, List, Any, Optional

from .base import DatabaseInterface
from ..errors import DatabaseError

logger = logging.getLogger(__name__)

class IndexManager:
    """
    Generic index management that handles both native and synthetic indexes.
    Works with any database implementation through the DatabaseInterface.
    """
    
    def __init__(self, db: DatabaseInterface):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self._supports_native_indexes = None  # Cache the result
    
    async def initialize_indexes(self, collections_structure: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Initialize indexes for all collections.
        
        Args:
            collections_structure: Dict mapping collection names to their required indexes
        """
        self.logger.info("Managing indexes for collections...")
        
        # Check native index support once
        if self._supports_native_indexes is None:
            self._supports_native_indexes = await self.db.supports_native_indexes()
            
        for collection, required_indexes in collections_structure.items():
            await self._manage_collection_indexes(collection, required_indexes)
    
    async def _manage_collection_indexes(self, collection: str, required_indexes: List[Dict[str, Any]]) -> None:
        """
        Manage indexes for a specific collection.
        
        Args:
            collection: Collection name
            required_indexes: List of required index definitions
        """
        self.logger.info(f"--- Managing indexes for collection '{collection}' ---")
        
        if not required_indexes:
            return
        
        # List required indexes
        self.logger.info(f"  Required indexes for '{collection}':")
        for idx in required_indexes:
            fields = idx.get('fields', [])
            fields_str = " + ".join(fields) if len(fields) > 1 else (fields[0] if fields else 'unknown')
            unique_str = " (UNIQUE)" if idx.get('unique') else ""
            self.logger.info(f"    - {idx.get('name', 'unnamed')}: {fields_str}{unique_str}")
        
        try:
            if self._supports_native_indexes:
                await self._manage_native_indexes(collection, required_indexes)
            else:
                await self._manage_synthetic_indexes(collection, required_indexes)
                
        except Exception as e:
            self.logger.error(f"Failed to manage indexes for collection '{collection}': {str(e)}")
            raise
    
    async def _manage_native_indexes(self, collection: str, required_indexes: List[Dict[str, Any]]) -> None:
        """Manage native database indexes (MongoDB, PostgreSQL, etc.)"""
        try:
            # Get existing indexes
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
            
            # Create missing indexes - compare by field composition, not name
            existing_index_signatures = {tuple(sorted(idx['fields'])) for idx in existing_indexes}
            missing_indexes = []
            
            for idx in required_indexes:
                required_signature = tuple(sorted(idx['fields']))
                if required_signature not in existing_index_signatures:
                    missing_indexes.append(idx)
            
            if missing_indexes:
                self.logger.info(f"  Creating missing indexes for '{collection}'")
                # Use the database's index creation method directly
                if hasattr(self.db, '_create_required_indexes'):
                    await self.db._create_required_indexes(collection, missing_indexes)
                else:
                    # Fallback to create_collection for databases that don't have direct index creation
                    await self.db.create_collection(collection, missing_indexes)
            
        except Exception as e:
            self.logger.error(f"Failed to manage native indexes for collection '{collection}': {str(e)}")
            raise
    
    async def _manage_synthetic_indexes(self, collection: str, required_indexes: List[Dict[str, Any]]) -> None:
        """Manage synthetic indexes (Elasticsearch, DynamoDB, etc.)"""
        try:
            # For synthetic indexes, we need to:
            # 1. Ensure hash fields exist for multi-field unique constraints
            # 2. Create regular (non-unique) indexes on those hash fields for performance
            # 3. Create indexes on single fields for performance
            
            indexes_to_create = []
            
            for idx in required_indexes:
                fields = idx.get('fields', [])
                unique = idx.get('unique', False)
                
                if not unique:
                    # Non-unique indexes - just create regular indexes
                    indexes_to_create.extend([{
                        'field': field,
                        'unique': False,
                        'name': f"{field}_idx"
                    } for field in fields])
                else:
                    # Unique constraints
                    if len(fields) == 1:
                        # Single field unique - create regular index (uniqueness handled by validation)
                        indexes_to_create.append({
                            'field': fields[0],
                            'unique': False,  # Synthetic - uniqueness handled by validation
                            'name': f"{fields[0]}_unique_idx"
                        })
                    else:
                        # Multi-field unique - create index on hash field
                        hash_field_name = self.db._get_hash_field_name(fields)
                        indexes_to_create.append({
                            'field': hash_field_name,
                            'unique': False,  # Synthetic - uniqueness handled by validation
                            'name': f"{'_'.join(sorted(fields))}_hash_idx"
                        })
            
            # Create the indexes
            if indexes_to_create:
                self.logger.info(f"  Creating synthetic indexes for '{collection}':")
                for idx_info in indexes_to_create:
                    field_name = idx_info['field']
                    idx_name = idx_info['name']
                    self.logger.info(f"    - {idx_name}: {field_name}")
                    
                    # Create single-field index
                    await self._create_synthetic_index(collection, field_name, idx_name)
            
        except Exception as e:
            self.logger.error(f"Failed to manage synthetic indexes for collection '{collection}': {str(e)}")
            raise
    
    async def _create_synthetic_index(self, collection: str, field: str, index_name: str) -> None:
        """Create a single synthetic index"""
        try:
            # This will be database-specific - delegate to the database implementation
            if hasattr(self.db, 'create_single_field_index'):
                await self.db.create_single_field_index(collection, field, index_name)
            else:
                # Fallback - log that index creation is not supported
                self.logger.warning(f"Database does not support synthetic index creation for field '{field}'")
        except Exception as e:
            self.logger.warning(f"Failed to create synthetic index '{index_name}' on field '{field}': {str(e)}")
            # Continue with other indexes
    
    async def reset_indexes(self, collections: List[str]) -> None:
        """Reset indexes for collections"""
        self.logger.info("Starting index reset...")
        
        # Check native index support
        if self._supports_native_indexes is None:
            self._supports_native_indexes = await self.db.supports_native_indexes()
        
        for collection in collections:
            await self._reset_collection_indexes(collection)
        
        self.logger.info("Index reset completed successfully")
    
    async def _reset_collection_indexes(self, collection: str) -> None:
        """Reset indexes for a specific collection"""
        self.logger.info(f"--- Resetting indexes for collection '{collection}' ---")
        
        try:
            if self._supports_native_indexes:
                # Use existing native index reset logic
                existing_indexes = await self.db.list_indexes(collection)
                self.logger.info(f"  Found {len(existing_indexes)} existing indexes")
                
                if not existing_indexes:
                    self.logger.info(f"  No indexes to reset for '{collection}'")
                    return
                
                # Filter out system indexes
                user_indexes = [
                    idx for idx in existing_indexes 
                    if not idx.get('name', '').startswith('_') and 
                       idx.get('name', '') != '_id_' and
                       not idx.get('system', False)
                ]
                
                if not user_indexes:
                    self.logger.info(f"  No user-defined indexes to remove for '{collection}'")
                    return
                
                self.logger.info(f"  Removing {len(user_indexes)} user-defined indexes")
                for idx in user_indexes:
                    fields = idx.get('fields', [])
                    if fields:
                        try:
                            await self.db.delete_index(collection, fields)
                        except Exception as e:
                            self.logger.warning(f"    Failed to delete index {idx.get('name', 'unnamed')}: {str(e)}")
            else:
                # For synthetic indexes, we might need to clean up hash fields
                # This is more complex and might require examining documents
                self.logger.info(f"  Synthetic index reset not yet implemented for '{collection}'")
                
        except Exception as e:
            self.logger.error(f"Failed to reset indexes for collection '{collection}': {str(e)}")
            raise