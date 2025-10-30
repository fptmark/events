"""
YAML schema generator
"""
from typing import Dict, Any
import yaml


class YAMLGenerator:
    """Generate YAML schema file from enriched schema"""

    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize YAML generator

        Args:
            schema: Enriched schema from analyzer
        """
        self.schema = schema

    def generate(self, output_file: str):
        """
        Generate YAML file

        Args:
            output_file: Output file path
        """
        yaml_data = {"_entities": {}}

        for entity_name, entity_data in sorted(self.schema.items()):
            entity_yaml = {"fields": {}}

            # Convert fields
            for field_name, field_meta in sorted(entity_data["fields"].items()):
                field_yaml = self._convert_field(field_meta)
                entity_yaml["fields"][field_name] = field_yaml

            # Add unique constraints
            indexes = entity_data.get("indexes", [])
            unique_indexes = [idx for idx in indexes if idx.get("unique")]
            if unique_indexes:
                entity_yaml["unique"] = [idx["fields"] for idx in unique_indexes]

            yaml_data["_entities"][entity_name] = entity_yaml

        # Write YAML file
        with open(output_file, 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

    def _convert_field(self, field_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Convert field metadata to YAML format"""
        field_yaml = {}

        # Type
        field_yaml["type"] = field_meta.get("type", "String")

        # Required
        if "required" in field_meta:
            field_yaml["required"] = field_meta["required"]

        # Enum
        if "enum" in field_meta:
            field_yaml["enum"] = {
                "values": field_meta["enum"]
            }

        # Pattern
        if "pattern" in field_meta:
            pattern = field_meta["pattern"]
            if pattern == "email":
                field_yaml["pattern"] = {
                    "regex": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                    "message": "Invalid email format"
                }
            elif pattern == "phone":
                field_yaml["pattern"] = {
                    "regex": "^[\\d\\s\\-\\+\\(\\)]{10,}$",
                    "message": "Invalid phone format"
                }
            elif pattern == "url":
                field_yaml["pattern"] = {
                    "regex": "^https?://[^\\s]+$",
                    "message": "Invalid URL format"
                }

        # Numeric range (use 'ge' and 'le' to match existing schema)
        if "min" in field_meta:
            field_yaml["ge"] = field_meta["min"]
        if "max" in field_meta:
            field_yaml["le"] = field_meta["max"]

        # String length
        if "min_length" in field_meta:
            field_yaml["min_length"] = field_meta["min_length"]
        if "max_length" in field_meta:
            field_yaml["max_length"] = field_meta["max_length"]

        return field_yaml
