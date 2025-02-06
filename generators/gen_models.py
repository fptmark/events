#!/usr/bin/env python
import sys
import os
from jinja2 import Environment, FileSystemLoader
import helpers

############################
# CUSTOM FILTER
############################
def model_field_filter(field_data: dict) -> str:
    """
    Convert a dict of validations (e.g., {'type': 'String', 'required': 'True', ...})
    into a Python type annotation for Pydantic:
      "Optional[str] = Field(None, min_length=3, regex='^https?://...')"
    """
    type_map = {
        'String': 'str',
        'Boolean': 'bool',
        'Number': 'float',
        'Integer': 'int',
        'ISODate': 'datetime',
        'ObjectId': 'PydanticObjectId',  # Use Beanie's type
        'JSON': 'dict'
    }

    field_type = field_data.get('type', 'String')
    py_type = type_map.get(field_type, 'str')

    required_val = field_data.get('required', False)
    if isinstance(required_val, str):
        required_val = (required_val.lower() == 'true')

    if required_val:
        base_type = py_type
        default_str = "Field(..."
    else:
        base_type = f"Optional[{py_type}]"
        default_str = "Field(None"

    field_params = []
    if 'minLength' in field_data:
        field_params.append(f"min_length={field_data['minLength']}")
    if 'maxLength' in field_data:
        field_params.append(f"max_length={field_data['maxLength']}")
    if 'pattern' in field_data:
        field_params.append(f"regex=r'{field_data['pattern']}'")
    if 'enum' in field_data:
        field_params.append(f"description='Allowed values: {field_data['enum']}'")
    if 'min' in field_data:
        field_params.append(f"ge={field_data['min']}")
    if 'max' in field_data:
        field_params.append(f"le={field_data['max']}")

    if field_params:
        default_str += ", " + ", ".join(field_params)
    default_str += ")"

    return f"{base_type} = {default_str}"

############################
# GEN MODELS
############################
def get_jinja_env(template_dir: str) -> Environment:
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True
    )
    return env

def generate_models(schema_file: str, path_root: str):
    print("Generating models...")

    models_dir = os.path.join(path_root, "app", "models")
    schema = helpers.get_schema(schema_file)

    template_dir = os.path.join(path_root, "generators", "templates", "models")
    env = get_jinja_env(template_dir)
    env.filters['model_field'] = model_field_filter

    try:
        base_entity_template = env.get_template("base_entity_model.j2")
    except Exception as e:
        base_entity_template = None

    model_template = env.get_template("model.j2")

    os.makedirs(models_dir, exist_ok=True)

    if "BaseEntity" in schema and base_entity_template:
        base_entity_def = schema["BaseEntity"]
        base_entity_fields = base_entity_def.get("fields", {})

        print("Generating BaseEntity.py...")
        rendered_base = base_entity_template.render(entity="BaseEntity", fields=base_entity_fields)
        base_entity_path = os.path.join(models_dir, "BaseEntity.py")
        with open(base_entity_path, "w") as f:
            f.write(rendered_base)
        print("BaseEntity.py generated.")

    special_keys = ["_relationships", "BaseEntity"]
    for entity_name, entity_def in schema.items():
        if entity_name in special_keys:
            continue

        inherits_base = (entity_def.get("inherits") == "BaseEntity")
        fields = entity_def.get("fields", {})

        rendered_model = model_template.render(
            entity=entity_name,
            fields=fields,
            inheritsBaseEntity=inherits_base
        )

        out_filename = f"{entity_name.lower()}_model.py"
        out_path = os.path.join(models_dir, out_filename)
        with open(out_path, "w") as f:
            f.write(rendered_model)

        print(f"Generated {out_filename}")

    print("Model generation complete!")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python gen_models.py <schema.yaml> <path_root>")
        sys.exit(1)

    schema_file = sys.argv[1]
    path_root = sys.argv[2]
    generate_models(schema_file, path_root)
