"""
Schema analyzer - Detect enums, validation rules, and patterns
"""
from typing import Dict, List, Any, Set
import re
import logging


class SchemaAnalyzer:
    """Analyze data to enrich schema with validation rules and metadata"""

    def __init__(self, db, sample_size: int = 100, verbose: bool = False):
        """
        Initialize analyzer

        Args:
            db: DatabaseInterface instance
            sample_size: Number of documents to sample per collection
            verbose: Enable verbose logging
        """
        self.db = db
        self.sample_size = sample_size
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)

    async def analyze_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze schema and enrich with validation rules

        Args:
            schema: Raw schema from introspector

        Returns:
            Enriched schema with validation metadata
        """
        enriched_schema = {}

        for entity_name, entity_data in schema.items():
            if self.verbose:
                print(f"  Analyzing: {entity_name}")

            enriched_fields = {}
            for field_name, field_meta in entity_data["fields"].items():
                enriched = await self._analyze_field(entity_name, field_name, field_meta)
                enriched_fields[field_name] = enriched

            enriched_schema[entity_name] = {
                "fields": enriched_fields,
                "indexes": entity_data["indexes"]
            }

        # Detect relationships (foreign keys)
        enriched_schema = self._detect_relationships(enriched_schema)

        return enriched_schema

    async def _analyze_field(
        self,
        entity_name: str,
        field_name: str,
        field_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a single field and enrich metadata

        Returns:
            Enriched field metadata with validation rules
        """
        enriched = field_meta.copy()

        # Sample field values
        values = await self._sample_field_values(entity_name, field_name)

        if not values:
            return enriched

        field_type = field_meta.get("type", "String")

        # Detect Currency based on field names (upgrade Number to Currency)
        if field_type in ["Number", "Float", "Integer"]:
            currency_keywords = ["amount", "price", "cost", "balance", "networth", "net_worth",
                               "salary", "fee", "charge", "payment", "total", "subtotal"]
            field_lower = field_name.lower()
            if any(keyword in field_lower for keyword in currency_keywords):
                enriched["type"] = "Currency"
                field_type = "Currency"
                if self.verbose:
                    print(f"    {field_name}: upgraded to Currency")

        # Detect enums (fields with limited distinct values)
        if field_type == "String":
            enum_values = self._detect_enum(values)
            if enum_values:
                enriched["enum"] = enum_values
                if self.verbose:
                    print(f"    {field_name}: enum {enum_values}")

        # Detect patterns (email, phone, etc.)
        if field_type == "String" and "enum" not in enriched:
            pattern = self._detect_pattern(values)
            if pattern:
                enriched["pattern"] = pattern
                if self.verbose:
                    print(f"    {field_name}: pattern {pattern}")

        # Detect min/max for numeric fields
        if field_type in ["Integer", "Float", "Currency"]:
            min_val, max_val = self._detect_numeric_range(values)
            if min_val is not None:
                enriched["min"] = min_val
            if max_val is not None:
                enriched["max"] = max_val
            if self.verbose and (min_val is not None or max_val is not None):
                print(f"    {field_name}: range [{min_val}, {max_val}]")

        # Detect string length constraints
        if field_type == "String" and "enum" not in enriched:
            min_len, max_len = self._detect_string_length(values)
            if min_len is not None and min_len > 0:
                enriched["min_length"] = min_len
            if max_len is not None:
                enriched["max_length"] = max_len

        return enriched

    async def _sample_field_values(self, entity_name: str, field_name: str) -> List[Any]:
        """Sample field values from database"""
        db_type = self.db.__class__.__name__

        if "Mongo" in db_type:
            db_conn = self.db.core.get_connection()
            cursor = db_conn[entity_name].find(
                {field_name: {"$exists": True, "$ne": None}},
                {field_name: 1, "_id": 0}
            ).limit(self.sample_size)

            documents = await cursor.to_list(length=self.sample_size)
            return [doc.get(field_name) for doc in documents if field_name in doc]
        else:
            raise NotImplementedError("Only MongoDB sampling implemented")

    def _detect_enum(self, values: List[Any], max_unique: int = 10) -> List[str]:
        """
        Detect if field is an enum

        Args:
            values: Sample values
            max_unique: Maximum unique values to consider as enum

        Returns:
            List of enum values, or empty list if not an enum
        """
        if not values:
            return []

        unique_values = set(str(v) for v in values if v is not None)

        # Consider enum if:
        # - Has <= max_unique distinct values
        # - At least 2 values
        # - Each value appears multiple times (not all unique)
        if len(unique_values) <= max_unique and len(unique_values) >= 2:
            if len(values) > len(unique_values) * 2:  # Repeated values
                return sorted(list(unique_values))

        return []

    def _detect_pattern(self, values: List[Any]) -> str:
        """
        Detect common patterns (email, phone, URL, etc.)

        Returns:
            Pattern name or empty string
        """
        if not values:
            return ""

        # Sample first 20 non-null values
        sample = [str(v) for v in values[:20] if v is not None]
        if not sample:
            return ""

        # Email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if all(re.match(email_pattern, v) for v in sample):
            return "email"

        # Phone pattern (various formats)
        phone_pattern = r'^[\d\s\-\+\(\)]{10,}$'
        if all(re.match(phone_pattern, v) for v in sample):
            return "phone"

        # URL pattern
        url_pattern = r'^https?://'
        if all(re.match(url_pattern, v) for v in sample):
            return "url"

        return ""

    def _detect_numeric_range(self, values: List[Any]) -> tuple:
        """
        Detect min/max values for numeric fields

        Returns:
            (min_value, max_value)
        """
        if not values:
            return (None, None)

        numeric_values = [v for v in values if isinstance(v, (int, float))]
        if not numeric_values:
            return (None, None)

        return (min(numeric_values), max(numeric_values))

    def _detect_string_length(self, values: List[Any]) -> tuple:
        """
        Detect min/max string lengths

        Returns:
            (min_length, max_length)
        """
        if not values:
            return (None, None)

        lengths = [len(str(v)) for v in values if v is not None]
        if not lengths:
            return (None, None)

        return (min(lengths), max(lengths))

    def _detect_relationships(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect relationships (foreign keys) based on naming conventions

        Looks for fields ending in 'Id' that reference other entities
        """
        entity_names = set(schema.keys())

        for entity_name, entity_data in schema.items():
            relationships = []

            for field_name, field_meta in entity_data["fields"].items():
                # Check if field ends with 'Id' and is ObjectId type
                if field_name.endswith("Id") and field_meta.get("type") == "ObjectId":
                    # Extract potential entity name (e.g., "accountId" -> "Account")
                    potential_ref = field_name[:-2]  # Remove 'Id'

                    # Capitalize first letter to match entity naming convention
                    potential_entity = potential_ref[0].upper() + potential_ref[1:]

                    # Check if this entity exists in schema
                    if potential_entity in entity_names:
                        relationships.append({
                            "field": field_name,
                            "references": potential_entity
                        })

            if relationships:
                entity_data["relationships"] = relationships

        return schema
