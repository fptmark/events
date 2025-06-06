"""
Database abstraction layer for the application.

Provides a runtime-selectable database backend system that supports
multiple database types (Elasticsearch, MongoDB, etc.) through a
common interface.

Usage:
    # Initialize database at startup
    from app.db import DatabaseFactory
    
    db = DatabaseFactory.create("elasticsearch")
    await db.init("http://localhost:9200", "mydb")
    DatabaseFactory.set_instance(db, "elasticsearch")
    
    # Use in models
    db = DatabaseFactory.get_instance()
    result = await db.find_all("users", User)
"""

from .base import DatabaseInterface
from .factory import DatabaseFactory
from .elasticsearch import ElasticsearchDatabase

# For backward compatibility, expose DatabaseFactory as Database
Database = DatabaseFactory

__all__ = [
    "DatabaseInterface", 
    "DatabaseFactory", 
    "Database",
    "ElasticsearchDatabase"
]