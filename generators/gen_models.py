import yaml
from pathlib import Path
import sys

# Paths
MODELS_DIR = Path("app/models")
RESERVED_TYPES = {"ISODate", "ObjectId"}  # Reserved types to skip


def generate_models(schema_path, path_root):
    """
    Generate Pydantic/Beanie models for the provided schema.
    """
    # Load the YAML schema
    with open(schema_path, "r") as file:
        schema = yaml.safe_load(file)

    # Extract entity definitions from the schema
    schemas = schema.get("components", {}).get("schemas", {})

    # Ensure the models directory exists
    output_dir = Path(path_root) / MODELS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    for entity_name, entity_schema in schemas.items():
        if entity_name in RESERVED_TYPES:
            continue  # Skip reserved types

        # Convert entity name to lowercase for file naming
        model_file = output_dir / f"{entity_name.lower()}_model.py"

        # Start building the model content
        lines = [
            "from beanie import Document",
            "from pydantic import Field",
            "from typing import Optional, List, Dict",
            "from datetime import datetime",
            "",
            f"class {entity_name}(Document):",
        ]

        # Add properties from the schema
        properties = entity_schema.get("properties", {})
        for prop_name, prop_details in properties.items():
            prop_type = prop_details.get("type", "string")
            prop_format = prop_details.get("format", "")
            python_type = {
                "string": "str",
                "integer": "int",
                "boolean": "bool",
                "number": "float",
                "array": "List",
                "object": "Dict",
            }.get(prop_type, "Any")

            # Handle special formats (e.g., date-time)
            if prop_format == "date-time":
                python_type = "datetime"

            # Skip reserved formats
            if prop_format in RESERVED_TYPES:
                continue

            # Add the field to the model
            field_def = f"    {prop_name}: Optional[{python_type}] = Field(None"
            if prop_name == "_id":
                field_def += ', alias="_id"'
            field_def += ")"
            lines.append(field_def)

        # Save the model file
        with open(model_file, "w") as model:
            model.write("\n".join(lines) + "\n")
        print(f">>> Generated {model_file}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gen_models.py <schema.yaml> <path_root")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_models(schema_file, path_root)
