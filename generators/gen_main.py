import yaml
from pathlib import Path
import sys

# Paths
MAIN_FILE = Path("app/main.py")
RESERVED_TYPES = {"ISODate", "ObjectId"}  # Reserved types to skip


def generate_main(schema_path):
    # Load the YAML schema
    with open(schema_path, "r") as file:
        schema = yaml.safe_load(file)

    # Extract entity names from the schema
    schemas = schema.get("components", {}).get("schemas", {})
    entity_names = [name for name in schemas.keys() if name not in RESERVED_TYPES]

    # Start building the main.py content
    lines = [
        "from fastapi import FastAPI",
        "from app.utils.db import init_db",
        "import json",
        "from pathlib import Path",
        "",
        "# Path to the configuration file",
        "CONFIG_FILE = Path('app/config.json')",
        "",
        "def load_config():",
        '    """',
        "    Load and return the configuration from config.json.",
        '    """',
        "    if not CONFIG_FILE.exists():",
        "        raise FileNotFoundError(f'Configuration file not found: {CONFIG_FILE}')",
        "    with open(CONFIG_FILE, 'r') as file:",
        "        return json.load(file)",
        "",
    ]

    # Import routes dynamically for valid entities
    for entity in entity_names:
        lines.append(f"from app.routes.{entity.lower()}_routes import router as {entity.lower()}_router")

    # Initialize FastAPI app
    lines.extend([
        "",
        "app = FastAPI()",
        "",
        "@app.on_event('startup')",
        "async def startup_event():",
        "    await init_db()  # Initialize MongoDB connection",
        "",
        "# Include routers",
    ])

    # Register routes dynamically
    for entity in entity_names:
        lines.append(f"app.include_router({entity.lower()}_router, prefix='/{entity.lower()}', tags=['{entity}'])")

    # Add root endpoint
    lines.extend([
        "",
        "@app.get('/')",
        "def read_root():",
        "    return {'message': 'Welcome to the Event Management System'}",
        "",
        "if __name__ == '__main__':",
        "    import uvicorn",
        "    try:",
        "        config = load_config()",
        "    except FileNotFoundError:",
        "        config = {",
        "            'host': '0.0.0.0',",
        "            'app_port': 8000,",
        "            'reload_dirs': ['app'],",
        "        }",
        f"    uvicorn.run(",
        "        app,",
        "        host=config.get('host', '0.0.0.0'),",
        "        port=config.get('app_port', 8000),",
        "        reload=True,",
        "        reload_dirs=config.get('reload_dirs', ['app']),",
        "    )",
    ])

    # Save main.py
    MAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MAIN_FILE, "w") as main_file:
        main_file.write("\n".join(lines) + "\n")
    print(f">>> Generated {MAIN_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main_generator.py <schema.yaml>")
        sys.exit(1)

    schema_file = sys.argv[1]
    generate_main(schema_file)
