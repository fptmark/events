"""
Database introspector - Extract raw schema from database
"""
from typing import Dict, List, Any, Set
import logging


class DatabaseIntrospector:
    """Extract schema information from database"""

    def __init__(self, db, verbose: bool = False):
        """
        Initialize introspector

        Args:
            db: DatabaseInterface instance from DatabaseFactory
            verbose: Enable verbose logging
        """
        self.db = db
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)

    async def extract_schema(self) -> Dict[str, Any]:
        """
        Extract complete schema from database

        Returns:
            Dict with structure:
            {
                "EntityName": {
                    "fields": {
                        "fieldName": {
                            "type": "String|Integer|Boolean|...",
                            "required": bool
                        }
                    },
                    "indexes": [
                        {"fields": ["field1"], "unique": True},
                        {"fields": ["field1", "field2"], "unique": True}
                    ]
                }
            }
        """
        schema = {}

        # Get all collections/tables
        collections = await self._get_collections()

        if self.verbose:
            print(f"  Found collections: {', '.join(collections)}")

        for collection in collections:
            if self.verbose:
                print(f"  Processing: {collection}")

            # Get fields by sampling documents
            fields = await self._get_fields(collection)

            # Get indexes
            indexes = await self._get_indexes(collection)

            schema[collection] = {
                "fields": fields,
                "indexes": indexes
            }

            if self.verbose:
                print(f"    - {len(fields)} fields")
                print(f"    - {len(indexes)} unique indexes")

        return schema

    async def _get_collections(self) -> List[str]:
        """Get list of all collections/tables"""
        db_type = self.db.__class__.__name__

        if "Mongo" in db_type:
            db_conn = self.db.core.get_connection()
            collections = await db_conn.list_collection_names()
            return collections
        elif "Postgres" in db_type or "SQLite" in db_type:
            # For SQL databases, query system tables
            # TODO: Implement SQL schema introspection
            raise NotImplementedError(f"SQL introspection not yet implemented for {db_type}")
        elif "Elasticsearch" in db_type:
            # For Elasticsearch, get indices
            # TODO: Implement ES schema introspection
            raise NotImplementedError(f"Elasticsearch introspection not yet implemented")
        else:
            raise NotImplementedError(f"Unknown database type: {db_type}")

    async def _get_fields(self, collection: str, sample_size: int = 100) -> Dict[str, Dict[str, Any]]:
        """
        Get fields and types by sampling documents

        Args:
            collection: Collection/table name
            sample_size: Number of documents to sample

        Returns:
            Dict of field metadata: {field_name: {type, required}}
        """
        db_type = self.db.__class__.__name__

        if "Mongo" in db_type:
            return await self._get_fields_mongo(collection, sample_size)
        else:
            raise NotImplementedError(f"Field introspection not implemented for {db_type}")

    async def _get_fields_mongo(self, collection: str, sample_size: int) -> Dict[str, Dict[str, Any]]:
        """Get fields from MongoDB by sampling documents"""
        db_conn = self.db.core.get_connection()

        # Sample documents
        cursor = db_conn[collection].find().limit(sample_size)
        documents = await cursor.to_list(length=sample_size)

        if not documents:
            return {}

        # Collect all field names and types
        field_types: Dict[str, Set[str]] = {}
        field_counts: Dict[str, int] = {}
        total_docs = len(documents)

        for doc in documents:
            for field, value in doc.items():
                if field not in field_types:
                    field_types[field] = set()
                    field_counts[field] = 0

                field_counts[field] += 1
                field_types[field].add(self._infer_type(value))

        # Build field metadata
        fields = {}
        for field, types in field_types.items():
            # Skip internal _id field
            if field == "_id":
                continue

            # Remove Null from types set to determine actual type
            non_null_types = types - {"Null"}

            # Determine field type
            if len(non_null_types) == 0:
                # All values are null
                field_type = "Null"
            elif len(non_null_types) == 1:
                # Single type (ignoring nulls)
                field_type = list(non_null_types)[0]
            else:
                # Multiple actual types - this is truly mixed
                field_type = "Mixed"

            # Field is required only if present in ALL documents with non-null values
            required = (field_counts[field] == total_docs) and "Null" not in types

            fields[field] = {
                "type": field_type,
                "required": required
            }

        return fields

    def _infer_type(self, value: Any) -> str:
        """Infer schema type from Python value"""
        from bson import ObjectId
        from datetime import datetime, date

        if value is None:
            return "Null"
        elif isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, int):
            return "Integer"
        elif isinstance(value, float):
            return "Number"  # Use Number instead of Float for better schema compatibility
        elif isinstance(value, str):
            return "String"
        elif isinstance(value, datetime):
            # Check if time component is midnight (00:00:00)
            if value.hour == 0 and value.minute == 0 and value.second == 0 and value.microsecond == 0:
                return "Date"
            return "Datetime"
        elif isinstance(value, date):
            return "Date"
        elif isinstance(value, ObjectId):
            return "ObjectId"
        elif isinstance(value, list):
            if value:
                elem_type = self._infer_type(value[0])
                return f"Array[{elem_type}]"
            return "Array"
        elif isinstance(value, dict):
            return "Object"
        else:
            return "Unknown"

    async def _get_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """Get all unique indexes for collection"""
        db_type = self.db.__class__.__name__

        if "Mongo" in db_type:
            return await self._get_indexes_mongo(collection)
        else:
            raise NotImplementedError(f"Index introspection not implemented for {db_type}")

    async def _get_indexes_mongo(self, collection: str) -> List[Dict[str, Any]]:
        """Get indexes from MongoDB"""
        db_conn = self.db.core.get_connection()
        indexes = []

        cursor = db_conn[collection].list_indexes()

        async for index_info in cursor:
            # Skip internal _id index
            if index_info.get("name") == "_id_":
                continue

            # Only track unique indexes
            if not index_info.get("unique", False):
                continue

            # Extract field names from index spec
            fields = []
            for field_name, _ in index_info.get("key", {}).items():
                fields.append(field_name)

            indexes.append({
                "fields": fields,
                "unique": True,
                "name": index_info.get("name")
            })

        return indexes
