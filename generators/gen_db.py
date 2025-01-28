import yaml
from pathlib import Path
import sys
import helpers

# Paths
DB_FILE = Path("app/utils/db.py")
RESERVED_TYPES = {"ISODate", "ObjectId"}  # Reserved types to skip
TEMPLATE = "generators/templates/db/db.txt"

def generate_db(schema_path, path_root):
    """
    Generate the db.py file for MongoDB connection and Beanie initialization.
    """
    # Load the YAML schema
    with open(schema_path, "r") as file:
        schema = yaml.safe_load(file)

    # Extract model names
    schemas = schema.get("components", {}).get("schemas", {})
    model_names = [name for name in schemas.keys() if name not in RESERVED_TYPES]

    # Generate db.py
    db_lines = [
        "from motor.motor_asyncio import AsyncIOMotorClient\n",
        "from beanie import init_beanie\n",
        "import logging\n",
        "\n",
    ]

    # Dynamically add imports for each model
    for model in model_names:
        db_lines.append(f"from app.models.{model.lower()}_model import {model}\n")

    template = helpers.read_file_to_array(TEMPLATE)
    models = ', '.join(model_names)
    template = [ line.replace("{models}", models) for line in template]

    db_lines.extend(template)

    # Ensure the directory exists
    outfile = helpers.generate_file(path_root, DB_FILE, db_lines)
    print(f">>> Generated {outfile}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gen_db.py <schema.yaml> <path_root")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_db(schema_file, path_root)
