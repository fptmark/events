from pathlib import Path
import sys
from typing import Type

import yaml

def generate_file(path_root: str, file_name: Path, lines)-> Path:
    outfile = Path(path_root) / file_name
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with open(outfile, "w") as main_file:
        if isinstance(lines, str):
            main_file.write(lines)
        else: 
            main_file.writelines(lines) 
    return outfile


def read_file_to_array(template: str, num=0)-> list[str]:
    """
    Reads the content of a file and returns it as an array of strings.

    Args:
        file_name (str): The name or path of the file to be read.

    Returns:
        list[str]: A list of strings, where each string is a line in the file.
    """
    try:
        file_name = f"{template}{num}.txt" if num > 0 else template
        with open(file_name, 'r', encoding='utf-8') as file:
            return file.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
        return []
    except IOError as e:
        print(f"Error reading the file '{file_name}': {e}")
        return []

# Example usage:
#file_content = read_file_to_array('example.txt')
# Function to convert plural entity names to singular (basic rule-based approach)

def singularize(name):
    if name.endswith("ies"):  # e.g., categories → category
        return name[:-3] + "y"
    elif name.endswith("s") and not name.endswith("ss"):  # e.g., users → user (but not addresses)
        return name[:-1]
    return name  # Default: leave it unchanged

RESERVED_TYPES = {"ISODate", "ObjectId", "_relationships"}
def get_schema(schema_path: str, reserved_types=RESERVED_TYPES)-> dict:
    with open(schema_path, "r") as file:
        schema = yaml.safe_load(file)

    # Extract entity schemas, skipping reserved types and metadata keys
    entity_schemas = {
        name: details for name, details in schema.items() if name not in reserved_types and isinstance(details, dict)
    }
    # print(f"{entity_schemas}")#['name']}")
    return entity_schemas

def pluralize(name) -> str:

    if name.endswith("y"):  # e.g., category → categories
        return name[:-1] + "ies"
    return name + "s"  # Default: just add "s"