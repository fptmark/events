"""
MMD (Mermaid Entity Relationship Diagram) generator
"""
from typing import Dict, List, Any, TextIO


class MMDGenerator:
    """Generate MMD schema file from enriched schema"""

    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize MMD generator

        Args:
            schema: Enriched schema from analyzer
        """
        self.schema = schema

    def generate(self, output_file: str):
        """
        Generate MMD file

        Args:
            output_file: Output file path
        """
        with open(output_file, 'w') as f:
            # Write diagram header
            f.write("erDiagram\n")

            # Write each entity
            for entity_name, entity_data in sorted(self.schema.items()):
                f.write(f"\n    {entity_name} {{\n")

                # Build index lookup for single-field uniques
                indexes = entity_data.get("indexes", [])
                single_field_uniques = set()
                composite_uniques = []

                for idx in indexes:
                    if idx.get("unique"):
                        if len(idx["fields"]) == 1:
                            single_field_uniques.add(idx["fields"][0])
                        else:
                            composite_uniques.append(idx["fields"])

                # Write fields
                for field_name, field_meta in sorted(entity_data["fields"].items()):
                    is_unique = field_name in single_field_uniques
                    self._write_field(f, field_name, field_meta, is_unique)

                # Write composite unique indexes before closing brace
                for fields in composite_uniques:
                    fields_str = '", "'.join(fields)
                    f.write(f'        %% @unique ["{fields_str}"]\n')

                f.write("    }\n")

            # Write relationships
            self._write_relationships(f)

    def _write_field(self, f: TextIO, field_name: str, field_meta: Dict[str, Any], is_unique: bool = False):
        """Write a single field line"""
        field_type = field_meta.get("type", "String")
        line = f"        {field_type} {field_name}"

        # Add validation metadata
        validation = self._build_validation(field_meta)
        if validation:
            line += f" %% @validate {{{validation}}}"

        # Add unique marker for single-field unique indexes
        if is_unique:
            line += ", @unique"

        line += "\n"
        f.write(line)

    def _build_validation(self, field_meta: Dict[str, Any]) -> str:
        """Build validation metadata string"""
        rules = []

        # Required
        if field_meta.get("required"):
            rules.append("required: true")
        else:
            rules.append("required: false")

        # Enum
        if "enum" in field_meta:
            enum_values = ", ".join(f'"{v}"' for v in field_meta["enum"])
            rules.append(f'enum: {{ values: [{enum_values}] }}')

        # Pattern
        if "pattern" in field_meta:
            pattern = field_meta["pattern"]
            if pattern == "email":
                rules.append('pattern: { regex: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}$" }')
            elif pattern == "phone":
                rules.append('pattern: { regex: "^[\\\\d\\\\s\\\\-\\\\+\\\\(\\\\)]{10,}$" }')
            elif pattern == "url":
                rules.append('pattern: { regex: "^https?://[^\\\\s]+$" }')

        # Numeric range
        if "min" in field_meta:
            rules.append(f'ge: {field_meta["min"]}')
        if "max" in field_meta:
            rules.append(f'le: {field_meta["max"]}')

        # String length
        if "min_length" in field_meta:
            rules.append(f'min_length: {field_meta["min_length"]}')
        if "max_length" in field_meta:
            rules.append(f'max_length: {field_meta["max_length"]}')

        return ", ".join(rules) if rules else ""

    def _write_relationships(self, f: TextIO):
        """Write relationship definitions"""
        f.write("\n")
        relationships_written = set()

        for entity_name, entity_data in self.schema.items():
            relationships = entity_data.get("relationships", [])
            for rel in relationships:
                ref_entity = rel["references"]
                # Avoid duplicate relationship definitions
                rel_key = f"{entity_name}->{ref_entity}"
                if rel_key not in relationships_written:
                    f.write(f'    {entity_name} ||--o{{ {ref_entity} : ""\n')
                    relationships_written.add(rel_key)
