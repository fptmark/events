from typing import List
import yaml
from pathlib import Path
import sys

import helpers

# Define the directory where models will be generated
MODELS_DIR = Path("app/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Path to the model template
TEMPLATE = "generators/templates/models/models.txt"

def map_python_type(yaml_type, constraints=None):
    """Map YAML types to Python types with optional constraints."""
    type_mapping = {
        "ObjectId": "str",
        "ISODate": "datetime",
        "String": "str",
        "Integer": "int",
        "Boolean": "bool",
        "Number": "float",
        "JSON": "Dict[str, Any]",
    }
    return type_mapping.get(yaml_type, "Any")

def generate_document_fields(fields):
    """Generate fields for the Beanie Document."""
    lines = []
    for field_name, field_info in fields.items():
        yaml_type = field_info.get("type", "String")
        python_type = map_python_type(yaml_type)
        required = field_info.get("required", "False") == "True"

        if field_name == "_id":
            # _id is always a string representation of ObjectId
            line = f"    _id: str"
        else:
            if required:
                line = f"    {field_name}: {python_type}"
            else:
                line = f"    {field_name}: Optional[{python_type}] = Field(None)"
        lines.append(line)
    return "\n".join(lines)

def generate_create_fields(fields):
    """Generate fields for the Create Pydantic model (exclude _id)."""
    lines = []
    for field_name, field_info in fields.items():
        if field_name == "_id":
            continue  # Exclude _id from Create model

        yaml_type = field_info.get("type", "String")
        python_type = map_python_type(yaml_type)
        required = field_info.get("required", "False") == "True"

        # Start field definition
        if not required:
            field_def = f"    {field_name}: Optional[{python_type}] = Field(None)"
        else:
            field_def = f"    {field_name}: {python_type}"

        # Add validations based on rules
        validations = []
        if "minLength" in field_info:
            validations.append(f"min_length={field_info['minLength']}")
        if "maxLength" in field_info:
            validations.append(f"max_length={field_info['maxLength']}")
        if "pattern" in field_info:
            validations.append(f"regex=r'{field_info['pattern']}'")
        if "min" in field_info:
            validations.append(f"ge={field_info['min']}")
        if "max" in field_info:
            validations.append(f"le={field_info['max']}")
        if "enum" in field_info:
            enum_values = field_info["enum"]
            enum_list = ", ".join([f"'{val}'" for val in enum_values])
            validations.append(f"enum=[{enum_list}]")

        if validations:
            field_def = field_def.split(" = ")[0] + f" = Field({', '.join(validations)})"
        elif not required:
            field_def += "  # Optional field"

        lines.append(field_def)
    return "\n".join(lines)

def generate_read_fields(fields):
    """Generate fields for the Read Pydantic model (include _id)."""
    lines = []
    for field_name, field_info in fields.items():
        yaml_type = field_info.get("type", "String")
        python_type = map_python_type(yaml_type)
        required = field_info.get("required", "False") == "True"

        if field_name == "_id":
            line = f"    _id: str"
        else:
            if required:
                line = f"    {field_name}: {python_type}"
            else:
                line = f"    {field_name}: Optional[{python_type}] = Field(None)"
        lines.append(line)
    return "\n".join(lines)

def singularize(name):
    """Basic singularization function."""
    if name.endswith('s'):
        return name[:-1]
    return name

def generate_model_file(model_name, fields, template_content: str):
    """Generate a model file based on the template."""
    substitution = {
        "ModelName": model_name,
        "collection_name": singularize(model_name).lower(),
        "DocumentFields": generate_document_fields(fields),
        "CreateFields": generate_create_fields(fields),
        "ReadFields": generate_read_fields(fields),
    }

    content = template_content
    for key, value in substitution.items():
        keyword = '{' + key + '}'
        content = content.replace(keyword, value)

    return content

def generate_models(schema_path, path_root):
    """Generate Pydantic and Beanie models based on the YAML schema."""
    # Load the YAML schema
    entities = helpers.get_schema(schema_path, "_relationships")

    # Read the model template
    with open(TEMPLATE, "r") as template_file:
        template_content = template_file.read()

    for entity_name, entity_info in entities.items():
        fields = entity_info.get("fields", {})
        if not isinstance(fields, dict):
            print(f"Error: 'fields' for {entity_name} is not a dictionary. Found: {type(fields).__name__}")
            continue

        # Capitalize the entity name for class definitions
        ModelName = entity_name

        # Generate model content
        model_content = generate_model_file(ModelName, fields, template_content)

        # Define the output model file path
        entity_singular = singularize(entity_name).lower()
        model_filename = helpers.generate_file(path_root, MODELS_DIR / f"{entity_singular}_model.py", model_content)

        print(f">>> Generated {model_filename}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python gen_model.py <schema.yaml> <path_root>")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_models(schema_file, path_root)
