import yaml
from pathlib import Path
import sys

# Paths
ROUTES_DIR = Path("app/routes")

# Reserved types that should not have routes generated
RESERVED_TYPES = {"ISODate", "ObjectId"}


def generate_routes(schema_path, path_root):
    # Load the YAML schema
    with open(schema_path, "r") as file:
        schema = yaml.safe_load(file)

    # Extract entity names from the schema
    schemas = schema.get("components", {}).get("schemas", {})
    entity_names = [name for name in schemas.keys() if name not in RESERVED_TYPES]

    # Ensure the routes directory exists
    # output_dir = path_root + '/' + ROUTES_DIR
    output_dir = Path(path_root) / ROUTES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    for entity in entity_names:
        # Convert entity name to lowercase for file naming
        route_file = output_dir / f"{entity.lower()}_routes.py"

        # Generate route content
        lines = [
            "from fastapi import APIRouter, HTTPException",
            "from typing import List",
            f"from app.models.{entity.lower()}_model import {entity}",
            "from app.utils.db import get_db",
            "from bson import ObjectId",
            "",
            "router = APIRouter()",
            "",
            "# CRUD Operations",
        ]

        # Add CRUD endpoints
        lines.extend([
            f"@router.post('/', response_model={entity})",
            f"async def create_{entity.lower()}(item: {entity}):",
            f"    db = get_db()",
            f"    item_dict = item.dict()",
            f"    item_dict['_id'] = str(ObjectId())",
            f"    await db['{entity.lower()}s'].insert_one(item_dict)",
            f"    return item_dict",
            "",
            f"@router.get('/', response_model=List[{entity}])",
            f"async def get_all_{entity.lower()}s():",
            f"    db = get_db()",
            f"    items = await db['{entity.lower()}s'].find().to_list(None)",
            f"    return items",
            "",
            f"@router.get('/{{item_id}}', response_model={entity})",
            f"async def get_{entity.lower()}(item_id: str):",
            f"    db = get_db()",
            f"    item = await db['{entity.lower()}s'].find_one({{'_id': ObjectId(item_id)}})",
            f"    if not item:",
            f"        raise HTTPException(status_code=404, detail='{entity} not found')",
            f"    return item",
            "",
            f"@router.put('/{{item_id}}', response_model={entity})",
            f"async def update_{entity.lower()}(item_id: str, item: {entity}):",
            f"    db = get_db()",
            f"    result = await db['{entity.lower()}s'].update_one({{'_id': ObjectId(item_id)}}, {{'$set': item.dict()}})",
            f"    if not result.matched_count:",
            f"        raise HTTPException(status_code=404, detail='{entity} not found')",
            f"    return item",
            "",
            f"@router.delete('/{{item_id}}')",
            f"async def delete_{entity.lower()}(item_id: str):",
            f"    db = get_db()",
            f"    result = await db['{entity.lower()}s'].delete_one({{'_id': ObjectId(item_id)}})",
            f"    if not result.deleted_count:",
            f"        raise HTTPException(status_code=404, detail='{entity} not found')",
            f"    return {{'message': '{entity} deleted successfully'}}",
        ])

        # Save the route file
        with open(route_file, "w") as route:
            route.write("\n".join(lines) + "\n")
        print(f">>> Generated {route_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python gen_db.py <schema.yaml> <path_root")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_routes(schema_file, path_root)