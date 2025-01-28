import yaml
from pathlib import Path
import sys
import helpers

# Paths
ROUTES_DIR = Path("app/routes")
TEMPLATE = Path("generators/templates/routes/routes.txt")

# Reserved types that should not have routes generated
RESERVED_TYPES = {"ISODate", "ObjectId"}


def generate_routes(schema_path, path_root):
    # Load the YAML schema
    with open(schema_path, "r") as file:
        schema = yaml.safe_load(file)

    # Extract entity names from the schema
    schemas = schema.get("components", {}).get("schemas", {})
    entity_names = [name for name in schemas.keys() if name not in RESERVED_TYPES]

    for entity in entity_names:
        entity_lower = entity.lower()

        # Convert entity name to lowercase for file naming
        route_file = f"{entity_lower}_routes.py"

        # Read the template file and replace placeholders
        template = helpers.read_file_to_array("generators/templates/routes/routes.txt")
        template = [ line.replace("{entity}", entity) for line in template] 
        template = [ line.replace("{entity_lower}", entity_lower) for line in template] 

    
        # Save the route file
        outfile = helpers.generate_file(path_root, ROUTES_DIR / route_file, template)
        print(f">>> Generated {outfile}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gen_db.py <schema.yaml> <path_root")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_routes(schema_file, path_root)