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
        "import sys",
        "from pathlib import Path",
        "",
        "# Add the project root to PYTHONPATH",
        "sys.path.append(str(Path(__file__).resolve().parent.parent))",
        "",
        "from fastapi import FastAPI",
        "from app.utils.db import init_db",
        "from app.utils.helpers import load_config",
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
        "    print('Startup event called')",
        "    config = load_config()",
        "    print(f\"Running in {'development' if config.get('environment', 'production') == 'development' else 'production'} mode\")",
        "    await init_db()",
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
        "",
        "    # Load configuration",
        "    config = load_config()",
        "",
        "    # Determine runtime mode",
        "    is_dev = config.get('environment', 'production') == 'development'",
        "",
        "    # Run Uvicorn",
        "    uvicorn.run(",
        "        'app.main:app',  # Use the import string for proper reload behavior",
        "        host=config.get('host', '0.0.0.0'),",
        "        port=config.get('app_port', 8000),",
        "        reload=is_dev,  # Enable reload only in development mode",
        "        reload_dirs=['app'] if is_dev else None,",
        "        log_level=config.get('log_level', 'info'),",
        "    )",
    ])

    # Save main.py
    MAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MAIN_FILE, "w") as main_file:
        main_file.write("\n".join(lines) + "\n")
    print(f">>> Generated {MAIN_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gen_main.py <schema.yaml>")
        sys.exit(1)

    schema_file = sys.argv[1]
    generate_main(schema_file)
