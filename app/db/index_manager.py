"""
Index management operations.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from app.services.metadata import MetadataService


class IndexManager(ABC):
    """Template Method Pattern - concrete orchestration, abstract worker methods"""
    
    def __init__(self, database):
        self.database = database
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> bool:
        """compare needed vs existing, delete obsolete, create missing"""
        try:
            for entity in MetadataService.list_entities():
                needed_uniques = MetadataService.get(entity).get('uniques', [])
                existing_indexes = await self.get_all(entity)
                for existing in existing_indexes:
                    if existing not in needed_uniques:
                        await self.delete(entity, existing)
                        self.logger.info(f"Deleted obsolete index on {entity}: {existing}")
                for needed in needed_uniques:
                    if needed not in existing_indexes:
                        await self.create(entity, needed, unique=True)
                        self.logger.info(f"Created missing index on {entity}: {needed}")
        except Exception as e:
            self.logger.error(f"Failed to initialize indexes: {str(e)}")
            return False
        return True

    async def reset(self) -> bool:
        """Reset indexes for all entities by deleting all non-system indexes"""
        self.logger.info("Starting index reset...")
        
        try:
            for entity in MetadataService.list_entities():
                existing_indexes = await self.get_all(entity)
                for existing in existing_indexes:
                    await self.delete(entity, existing)
                    self.logger.info(f"Deleted index on {entity}: {existing}")
        except Exception as e:
            self.logger.error(f"Failed to reset indexes: {str(e)}")
            return False
        return True
    
    # Abstract worker methods for database drivers to implement
    @abstractmethod
    async def get_all(self, entity: str) -> List[List[str]]:
        """Get all unique constraint field lists for entity"""
        pass

    @abstractmethod
    async def get_all_detailed(self, entity: str) -> dict:
        """Get all indexes with full details as dict[index_name, index_info]"""
        pass

    @abstractmethod
    async def create(self, entity: str, fields: List[str], unique: bool = True, name: Optional[str] = None) -> None:
        """Create unique index on entity"""
        pass

    @abstractmethod
    async def delete(self, entity: str, fields: List[str]) -> None:
        """Delete index by field names"""
        pass 