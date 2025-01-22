import yaml
from pathlib import Path
import sys

# Paths
DB_FILE = Path("app/utils/db.py")
HELPERS_FILE = Path("app/utils/helpers.py")

# Reserved types that should not be treated as models
RESERVED_TYPES = {"ISODate", "ObjectId"}


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
        "from bson.objectid import ObjectId",
        "from typing import Dict, Any, Optional",
        "import json",
        "from pathlib import Path",
        "",
        "# Path to the config file",
        "CONFIG_FILE = Path('app/config.json')",
        "",
        "def load_config():",
        '    """',
        "    Load and return the configuration from config.json.",
        '    """',
        "    if not CONFIG_FILE.exists():",
        "        raise FileNotFoundError(f'Configuration file not found: {CONFIG_FILE}')",
        "    with open(CONFIG_FILE, 'r') as config_file:",
        "        return json.load(config_file)",
        "",
    ]

    # Dynamically import valid models
    for model in model_names:
        db_lines.append(f"from app.models.{model.lower()}_model import {model}")

    db_lines.extend([
        "",
        "# MongoDB connection string",
        "client: Optional[AsyncIOMotorClient] = None",
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
    ])

    # Save db.py
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DB_FILE, "w") as db_file:
        db_file.write("\n".join(db_lines) + "\n")
    print(f">>> Generated {DB_FILE}")

    # Generate helpers.py
    helpers_lines = [
        "from bson.objectid import ObjectId",
        "from typing import Dict, Any",
        "",
        "def serialize_mongo_document(doc: Dict[str, Any]) -> Dict[str, Any]:",
        '    """',
        "    Serialize MongoDB document for JSON response.",
        "    Convert ObjectId to string.",
        '    """',
        "    if '_id' in doc and isinstance(doc['_id'], ObjectId):",
        "        doc['_id'] = str(doc['_id'])",
        "    return doc",
    ]

    # Save helpers.py
    with open(HELPERS_FILE, "w") as helpers_file:
        helpers_file.write("\n".join(helpers_lines) + "\n")
    print(f">>> Generated {HELPERS_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python db_generator.py <schema.yaml>")
        sys.exit(1)

    schema_file = sys.argv[1]
    generate_db(schema_file)
