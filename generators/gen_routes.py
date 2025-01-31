import yaml
from pathlib import Path
import sys
import helpers

# Paths
ROUTES_DIR = Path("app/routes")
TEMPLATE = Path("generators/templates/routes/routes.txt")

def singularize(name):
    """Basic singularization function."""
    if name.endswith('s'):
        return name[:-1]
    return name

def pluralize(name):
    """Basic pluralization function."""
    if not name.endswith('s'):
        return name + 's'
    return name

def map_python_type(yaml_type):
    """Map YAML types to Python types."""
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

def generate_fields(fields, model_type="Create"):
    """
    Generate Pydantic fields for Create or Read models.
    model_type: "Create" or "Read"
    """
    field_lines = []
    for field_name, rules in fields.items():
        if model_type == "Create" and field_name == "_id":
            continue  # Exclude _id from Create model
        
        yaml_type = rules.get("type", "String")
        python_type = map_python_type(yaml_type)
        required = rules.get("required", "False") == "True"

        # Start field definition
        if not required:
            field_def = f"    {field_name}: Optional[{python_type}] = Field(None)"
        else:
            field_def = f"    {field_name}: {python_type}"

        # Add validations based on rules
        validations = []
        if "minLength" in rules:
            validations.append(f"min_length={rules['minLength']}")
        if "maxLength" in rules:
            validations.append(f"max_length={rules['maxLength']}")
        if "pattern" in rules:
            validations.append(f"regex=r'{rules['pattern']}'")
        if "min" in rules:
            validations.append(f"ge={rules['min']}")
        if "max" in rules:
            validations.append(f"le={rules['max']}")
        if "enum" in rules:
            enum_values = rules["enum"]
            enum_list = ", ".join([f"'{val}'" for val in enum_values])
            validations.append(f"enum=[{enum_list}]")

        if validations and model_type == "Create":
            # Replace the default None with validations
            field_def = field_def.split(" = ")[0] + f" = Field({', '.join(validations)})"
        
        field_lines.append(field_def)
    
    return "\n".join(field_lines)

def generate_routes(schema_path, path_root):
    """
    Generate route files based on the YAML schema and template.
    """
    # Ensure the routes directory exists
    ROUTES_DIR.mkdir(parents=True, exist_ok=True)

    # Load the YAML schema
    entity_schemas = helpers.get_schema(schema_path)

    for entity, entity_schema in entity_schemas.items():
        fields = entity_schema.get("fields", {})
        if not isinstance(fields, dict):
            print(f"Error: 'fields' for {entity} is not a dictionary. Found: {type(fields).__name__}")
            continue

        # Create entity names
        entity_lower = entity.lower()
        entity_singular = singularize(entity_lower)
        entity_plural = pluralize(entity_singular)
        ModelName = entity

        # Generate Pydantic model fields
        create_fields = generate_fields(fields, model_type="Create")
        read_fields = generate_fields(fields, model_type="Read")

        # Read the template file
        with open(TEMPLATE, "r") as template_file:
            template_content = template_file.read()

        # Replace placeholders in the template
        template_content = template_content.replace("{ModelName}", ModelName)
        template_content = template_content.replace("{entity_lower}", entity_lower)
        template_content = template_content.replace("{entity_plural}", entity_plural)
        template_content = template_content.replace("{create_fields}", create_fields)
        template_content = template_content.replace("{read_fields}", read_fields)

        # Define the output route file path
        route_file = helpers.generate_file(path_root, ROUTES_DIR / f"{entity_lower}_routes.py", template_content)
        print(f">>> Generated {route_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python gen_routes.py <schema.yaml> <path_root>")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_routes(schema_file, path_root)
