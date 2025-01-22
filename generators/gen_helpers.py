from pathlib import Path
import sys

# Path for helpers.py
HELPERS_FILE = Path("app/utils/helpers.py")


def generate_helpers(path_root):
    """
    Generate the helpers.py file with utility functions for configuration loading and MongoDB serialization.
    """
    helpers_lines = [
        "import json",
        "from pathlib import Path",
        "from bson.objectid import ObjectId",
        "from typing import Dict, Any",
        "",
        "# Path to the configuration file",
        "CONFIG_FILE = Path('app/config.json')",
        "",
        "def load_config():",
        '    """',
        "    Load and return the configuration from config.json.",
        "    If the file is not found, return default configuration values.",
        '    """',
        "    if not CONFIG_FILE.exists():",
        "        print(f'Warning: Configuration file {CONFIG_FILE} not found. Using defaults.')",
        "        return {",
        "            'mongo_uri': 'mongodb://localhost:27017',",
        "            'db_name': 'default_db',",
        "            'app_port': 8000,",
        "            'environment': 'production',",
        "            'log_level': 'info',",
        "        }",
        "    with open(CONFIG_FILE, 'r') as config_file:",
        "        return json.load(config_file)",
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

    # Ensure the directory exists
    outfile = Path(path_root) / HELPERS_FILE
    outfile.parent.mkdir(parents=True, exist_ok=True)

    # Write the helpers.py file
    with open(outfile, "w") as helpers_file:
        helpers_file.write("\n".join(helpers_lines) + "\n")
    print(f">>> Generated {outfile}")

if __name__ == "__main__":
    if len(sys.argv) < 1:
        print("Usage: python gen_helpers.py <path_root")
        sys.exit(1)

    path_root = sys.argv[1]
    generate_helpers(path_root)
