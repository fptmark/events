#!/usr/bin/env python
import sys
import os
from jinja2 import Environment, FileSystemLoader
import helpers

def get_jinja_env(template_dir: str) -> Environment:
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True
    )
    # Optionally add built-ins here if needed
    return env

def generate_routes(schema_file: str, path_root: str):
    print("Generating routes...")
    schema = helpers.get_schema(schema_file)
    template_dir = os.path.join(path_root, 'generators', 'templates', 'routes')
    env = get_jinja_env(template_dir)
    route_template = env.get_template('route.j2')

    routes_dir = os.path.join(path_root, 'app', 'routes')
    os.makedirs(routes_dir, exist_ok=True)

    special_keys = ["_relationships", "BaseEntity"]
    for entity_name, entity_def in schema.items():
        if entity_name in special_keys:
            continue

        rendered = route_template.render(entity=entity_name)
        out_filename = f"{entity_name.lower()}_router.py"
        out_path = os.path.join(routes_dir, out_filename)
        with open(out_path, 'w') as f:
            f.write(rendered)
        print(f"Generated {out_filename}")
    print("Route generation complete!")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python gen_routes.py <schema.yaml> <path_root>")
        sys.exit(1)
    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_routes(schema_file, path_root)
