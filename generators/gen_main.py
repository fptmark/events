import yaml
from pathlib import Path
import sys
import helpers

# Paths
MAIN_FILE = Path("app/main.py")
RESERVED_TYPES = {"ISODate", "ObjectId"}  # Reserved types to skip
TEMPLATE = "generators/templates/main/main"

def generate_main(schema_path, path_root):

    entity_schemas = helpers.get_schema(schema_path)
    # with open(schema_path, "r") as file:
    #     schema = yaml.safe_load(file)

    # # Extract entity names from the schema
    # schemas = schema.get("components", {}).get("schemas", {})
    # entity_names = [name for name in schemas.keys() if name not in RESERVED_TYPES]

    # Start building the main.py content
    lines = helpers.read_file_to_array(TEMPLATE, 1)

    # Import routes dynamically for valid entities
    for entity, _ in entity_schemas.items():
        entity_lower = entity.lower()
        if entity_lower != 'baseentity':
            # print(f"from app.routes.{entity_lower}_routes import router as {entity_lower}_router\n")
            lines.append(f"from app.routes.{entity_lower}_router import router as {entity_lower}_router\n")

    # Initialize FastAPI app
    lines.extend( helpers.read_file_to_array(TEMPLATE, 2))

    # Register routes dynamically
    for entity, _ in entity_schemas.items():
        if entity.lower() != 'baseentity':
            lines.append(f"app.include_router({entity.lower()}_router, prefix='/{entity.lower()}', tags=['{entity}'])\n")

    # Add root endpoint
    lines.extend( helpers.read_file_to_array(TEMPLATE, 3))

    # Save main.py
    outfile = helpers.generate_file(path_root, MAIN_FILE, lines)
    print(f">>> Generated {outfile}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gen_main.py <schema.yaml> <path_root")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_main(schema_file, path_root)
