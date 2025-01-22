import yaml
from pathlib import Path
import sys

# Paths
MODELS_DIR = Path("app/models")


def generate_models(schema_path):
    # Load the YAML schema
    with open(schema_path, "r") as file:
        schema = yaml.safe_load(file)

    # Extract entity definitions from the schema
    schemas = schema.get("components", {}).get("schemas", {})

    # Ensure the models directory exists
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for entity_name, entity_schema in schemas.items():
        # Convert entity name to lowercase for file naming
        model_file = MODELS_DIR / f"{entity_name.lower()}_model.py"

        # Start building the model content
        lines = [
            "from beanie import Document",
            "from pydantic import Field",
            "from datetime import datetime",
            "from typing import Optional, List, Dict",
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

            # Handle special formats
            if prop_format == "date-time":
                python_type = "datetime"
            elif prop_format == "ObjectId":
                python_type = "str"

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
    if len(sys.argv) < 2:
        print("Usage: python models_generator.py <schema.yaml>")
        sys.exit(1)

    schema_file = sys.argv[1]
    generate_models(schema_file)
