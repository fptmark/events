"""
Entity/Collection management operations.
These are admin operations, not URL-driven.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class EntityManager(ABC):
    """Entity/Collection management operations"""
    
    @abstractmethod
    async def exists(self, entity_type: str) -> bool:
        """Check if entity collection exists"""
        pass
    
    @abstractmethod
    async def create(self, entity_type: str, unique_constraints: List[List[str]]) -> bool:
        """
        Create entity collection with unique indexes.
        
        Args:
            entity_type: Entity type (e.g., "user", "account")
            unique_constraints: List of field combinations for unique indexes
                               e.g., [["email"], ["username"], ["firstName", "lastName"]]
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_type: str) -> bool:
        """Delete entity collection"""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[str]:
        """Get all entity collection names"""
        pass