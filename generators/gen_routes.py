from pathlib import Path
import sys
import helpers

# Paths
ROUTES_DIR = Path("app/routes")
TEMPLATE = Path("generators/templates/routes/routes.txt")

# Reserved types and metadata keys that should not generate routes
# RESERVED_TYPES = {"ISODate", "ObjectId", "_relationships"}


def generate_routes(schema_path, path_root):
    # Load the YAML schema
    entity_schemas = helpers.get_schema(schema_path)

    # with open(schema_path, "r") as file:
    #     schema = yaml.safe_load(file)

    # # Extract entity schemas, skipping reserved types and metadata keys
    # entity_schemas = {
    #     name: details for name, details in schema.items() if name not in RESERVED_TYPES and isinstance(details, dict)
    # }

    for entity, entity_schema in entity_schemas.items():
        fields = entity_schema.get("fields", {})
        if not isinstance(fields, dict):
            print(f"Error: 'fields' for {entity} is not a dictionary. Found: {type(fields).__name__}")
            continue

        # Create entity names
        entity_lower = entity.lower()   
        entity_singular = helpers.singularize(entity_lower)
        entity_name = entity_singular.capitalize()  # Singular entity name with capital first letter

        # print(f"names {entity_singular} {entity_lower} {entity}")
        route_file = f"{entity_singular}_routes.py"  # Singular file name

        # Generate Pydantic model fields
        pydantic_fields = []
        for field, rules in fields.items():
            field_type = rules["type"]
            if field_type == "String":
                pydantic_type = "str"
            elif field_type == "Integer":
                pydantic_type = "int"
            elif field_type == "Number":
                pydantic_type = "float"
            elif field_type == "Boolean":
                pydantic_type = "bool"
            else:
                pydantic_type = "Any"

            field_definition = f"{field}: {pydantic_type}"
            if rules.get("required", False):
                field_definition += "  # Required"
            pydantic_fields.append(field_definition)

        # Validation logic for route handlers
        validation_imports = set()
        validation_code = []
        for field, rules in fields.items():
            if rules.get("required"):
                validation_code.append(f"    if not item.{field}: raise HTTPException(status_code=400, detail='Field {field} is required')")
            if "minLength" in rules:
                validation_code.append(f"    if len(item.{field}) < {rules['minLength']}: raise HTTPException(status_code=400, detail='Field {field} must have at least {rules['minLength']} characters')")
            if "maxLength" in rules:
                validation_code.append(f"    if len(item.{field}) > {rules['maxLength']}: raise HTTPException(status_code=400, detail='Field {field} must not exceed {rules['maxLength']} characters')")
            if "min" in rules:
                validation_code.append(f"    if item.{field} < {rules['min']}: raise HTTPException(status_code=400, detail='Field {field} must be at least {rules['min']}')")
            if "max" in rules:
                validation_code.append(f"    if item.{field} > {rules['max']}: raise HTTPException(status_code=400, detail='Field {field} must be at most {rules['max']}')")
            if "pattern" in rules:
                validation_imports.add("import re")
                validation_code.append(f"    if not re.match(r'{rules['pattern']}', item.{field}): raise HTTPException(status_code=400, detail='Field {field} does not match required pattern')")

        # Read the template file
        template = helpers.read_file_to_array("generators/templates/routes/routes.txt")

        # Replace placeholders in the template
        template = [line.replace("{entity_name}", entity_name) for line in template]
        template = [line.replace("{entity_singular}", entity_singular) for line in template]
        template = [line.replace("{entity_lower}", entity_lower) for line in template]
        template = [line.replace("{validation_code}", "\n".join(validation_code)) for line in template]
        template = [line.replace("{validation_imports}", "\n".join(validation_imports)) for line in template]
        template = [line.replace("{pydantic_fields}", "\n    ".join(pydantic_fields)) for line in template]

        # Save the route file
        outfile = helpers.generate_file(path_root, ROUTES_DIR / route_file, template)
        print(f">>> Generated {outfile}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gen_routes.py <schema.yaml> <path_root>")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_routes(schema_file, path_root)
