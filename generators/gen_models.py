import yaml
from pathlib import Path
import sys
import helpers

# Paths
MODELS_DIR = Path("app/models")
RESERVED_TYPES = {"ISODate", "ObjectId"}  # Reserved types to skip

# Function to map schema types to Python types
def map_python_type(prop_type, prop_format=""):
    type_mapping = {
        "String": "str",
        "Integer": "int",
        "Boolean": "bool",
        "Number": "float",
        "Array[String]": "List[str]",
        "Array[Integer]": "List[int]",
        "Array[Number]": "List[float]",
        "Array[Boolean]": "List[bool]",
        "Array[Object]": "List[Dict[str, Any]]",
        "Object": "Dict[str, Any]",
        "ISODate": "datetime",
    }
    if prop_format == "date-time":
        return "datetime"
    return type_mapping.get(prop_type, "Any")  # Default to Any


def generate_models(schema_path, path_root):
    """
    Generate Pydantic/Beanie models for the provided schema.
    """
    # Ensure the models directory exists
    output_dir = Path(path_root) / MODELS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load the YAML schema
    entity_schemas = helpers.get_schema(schema_path)
    # with open(schema_path, "r") as file:
    #     schema = yaml.safe_load(file)

    # # Extract entity definitions from the schema
    # entity_schemas = {
    #     name: details for name, details in schema.items() if name not in RESERVED_TYPES and isinstance(details, dict)
    # }

    for entity_name, entity_schema in entity_schemas.items():
        # if entity_name in RESERVED_TYPES:
        #     continue  # Skip reserved types

        # Convert entity name to lowercase for file naming
        entity_singular = helpers.singularize(entity_name.lower())
        model_file = output_dir / f"{entity_singular}_model.py"

        # Start building the model content
        lines = [
            "from beanie import Document",
            "from pydantic import Field",
            "from typing import List, Dict, Any, Optional",
            "from datetime import datetime",
            "",
            f"class {entity_singular.capitalize()}(Document):",
        ]

        # Add properties from the schema
        fields = entity_schema.get("fields", {})
        for field_name, field_details in fields.items():
            prop_type = field_details.get("type", "string")
            prop_format = field_details.get("format", "")
            required = field_details.get("required", False)  # Fix required detection

            # Ensure _id is a string for MongoDB
            if field_name == "_id":
                python_type = "str"
            else:
                python_type = map_python_type(prop_type, prop_format)

            # Fix optional/required fields
            if required is True or required == "True":
                field_def = f"    {field_name}: {python_type}"  # Required field
            else:
                field_def = f"    {field_name}: Optional[{python_type}] = Field(None)"  # Optional field
            
            lines.append(field_def)

        # Save the model file
        with open(model_file, "w") as model:
            model.write("\n".join(lines) + "\n")
        print(f">>> Generated {model_file}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gen_models.py <schema.yaml> <path_root>")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_models(schema_file, path_root)
