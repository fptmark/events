import yaml
from pathlib import Path
import sys

# Paths
DB_FILE = Path("app/utils/db.py")
RESERVED_TYPES = {"ISODate", "ObjectId"}  # Reserved types to skip


def generate_db(schema_path):
    # Load the YAML schema
    with open(schema_path, "r") as file:
        schema = yaml.safe_load(file)

    # Extract model names
    schemas = schema.get("components", {}).get("schemas", {})
    model_names = [name for name in schemas.keys() if name not in RESERVED_TYPES]

    # Generate db.py
    db_lines = [
        "from motor.motor_asyncio import AsyncIOMotorClient",
        "from beanie import init_beanie",
        "from app.utils.helpers import load_config",
        "",
        "# MongoDB connection string",
        "client = None",
        "",
        "async def init_db():",
        '    """',
        "    Initialize MongoDB connection and Beanie models.",
        '    """',
        "    global client",
        "    config = load_config()",
        "    client = AsyncIOMotorClient(config['mongo_uri'])",
        "    db = client[config['db_name']]",
        "",
        "    # Initialize Beanie models",
        f"    await init_beanie(database=db, document_models=[{', '.join(model_names)}])",
        "",
        "def get_db():",
        '    """',
        "    Get a direct connection to the MongoDB database.",
        '    """',
        "    if client is None:",
        '        raise Exception("Database client is not initialized. Call init_db() first.")',
        "    config = load_config()",
        "    return client[config['db_name']]",
    ]

    # Save db.py
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_FILE, "w") as db_file:
        db_file.write("\n".join(db_lines) + "\n")
    print(f">>> Generated {DB_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gen_db.py <schema.yaml>")
        sys.exit(1)

    schema_file = sys.argv[1]
    generate_db(schema_file)
