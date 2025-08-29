"""
New refactored database layer with clean separation of concerns.

Architecture:
- DatabaseInterface: Main interface that composes sub-managers
- DatabaseManager: Core operations (init, close, get_id)
- DocumentManager: CRUD operations (get, get_all, save, delete)
- EntityManager: Collection management (exists, create, delete)
- IndexManager: Index management (create, get_all, delete)
"""

from .base import DatabaseInterface
from .factory import DatabaseFactory

__all__ = ['DatabaseInterface', 'DatabaseFactory']