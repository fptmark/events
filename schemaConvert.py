import re
import yaml
from collections import defaultdict

def parse_validation_string(validation_str):
    """
    Parses a validation string like "{ type: ObjectId, required: true }"
    into a Python dictionary.
    """
    validation = {}
    # Remove the surrounding braces and whitespace
    validation_str = validation_str.strip().strip('{}').strip()

    # Split by commas to get key-value pairs, handling nested structures like enums
    # This regex splits on commas that are not inside brackets
    pairs = re.findall(r'(\w+):\s*(\[[^\]]+\]|[^,]+)', validation_str)

    for key, value in pairs:
        key = key.strip()
        value = value.strip()

        # Handle different value types
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        elif value.startswith('[') and value.endswith(']'):
            # Handle lists (e.g., enums)
            # Extract items, considering quotes
            items = re.findall(r"'([^']*)'|\"([^\"]*)\"|([^,\s]+)", value[1:-1])
            # Flatten the list and filter out empty strings
            items = [item[0] or item[1] or item[2] for item in items]
            value = items
        else:
            # Assume it's a string without quotes
            value = value.strip('\'"')  # Remove any surrounding quotes
        validation[key] = value
    return validation

def parse_mmd(mmd_content):
    entities = {}
    validations = {}
    relationships = []
    lines = mmd_content.splitlines()
    current_entity = None
    validation_entity = None

    # Regular expressions to match different parts of the MMD
    entity_pattern = re.compile(r'^(\w+)\s*\{')
    field_pattern = re.compile(r'^\s*(\w+)\s+([\w\[\]]+)')
    validation_start_pattern = re.compile(r'^%%\s*@validation\s+(\w+)')
    validation_field_pattern = re.compile(r'^%%\s+(\w+):\s*\{(.+)\}')
    relationship_pattern = re.compile(r'^(\w+)\s+\|\|--o\{\s*(\w+):.*$')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('erDiagram'):
            continue

        # Check for entity definition
        entity_match = entity_pattern.match(line)
        if entity_match:
            current_entity = entity_match.group(1)
            entities[current_entity] = {'fields': {}, 'relations': []}
            continue

        # Check for end of entity
        if line == '}':
            current_entity = None
            continue

        # Check for validation start
        validation_start_match = validation_start_pattern.match(line)
        if validation_start_match:
            validation_entity = validation_start_match.group(1)
            validations[validation_entity] = {}
            continue

        # Check for validation fields
        validation_field_match = validation_field_pattern.match(line)
        if validation_field_match and validation_entity:
            field_name = validation_field_match.group(1)
            field_validations_str = validation_field_match.group(2)
            # Parse the validation string manually
            try:
                field_validations = parse_validation_string(field_validations_str)
                validations[validation_entity][field_name] = field_validations
            except Exception as e:
                print(f"Error parsing validation for {validation_entity}.{field_name}: {e}")
            continue

        # Check for relationships
        relationship_match = relationship_pattern.match(line)
        if relationship_match:
            source = relationship_match.group(1)
            target = relationship_match.group(2)
            relationships.append({'source': source, 'target': target})
            continue

        # If inside an entity, parse fields
        if current_entity:
            field_match = field_pattern.match(line)
            if field_match:
                field_type = field_match.group(1)   # Corrected: type is group 1
                field_name = field_match.group(2)   # Corrected: name is group 2
                entities[current_entity]['fields'][field_name] = {'type': field_type}

    return entities, validations, relationships

def process_entities(entities, validations):
    processed = {}
    for entity, data in entities.items():
        # Use the entity name as-is, maintaining singular and PascalCase
        entity_key = entity
        processed[entity_key] = {'fields': {}, 'relations': []}
        fields = data['fields']
        entity_validations = validations.get(entity, {})
        for field, details in fields.items():
            field_info = {}
            field_type = details['type']
            # Handle Array types
            array_match = re.match(r'Array\[(\w+)\]', field_type)
            if array_match:
                base_type = array_match.group(1)
                field_info['type'] = f"Array[{base_type}]"
            else:
                field_info['type'] = field_type

            # Add validation data
            validation = entity_validations.get(field, {})
            # Required flag
            required = validation.get('required', False)
            # Ensure required is a string 'True'/'False'
            if isinstance(required, bool):
                required = 'True' if required else 'False'
            else:
                # In case it's a string like 'true'/'false'
                required = 'True' if str(required).lower() == 'true' else 'False'
            field_info['required'] = required

            # Add other validations
            for key, value in validation.items():
                if key != 'required':
                    field_info[key] = value

            processed[entity_key]['fields'][field] = field_info

        processed[entity_key]['relations'] = []  # Will fill later
        print(f"Processed Entity: {entity_key}")  # Debugging Statement
    return processed

def map_relationships(processed_entities, relationships):
    for rel in relationships:
        source = rel['source']
        target = rel['target']
        source_key = source  # Use exact entity name
        target_key = target  # Use exact entity name

        if source_key in processed_entities:
            processed_entities[source_key]['relations'].append(target_key)
            print(f"Mapped Relationship: {source_key} -> {target_key}")  # Debugging Statement
        else:
            print(f"Warning: Source entity '{source}' not found in entities.")

    return processed_entities

def build_relationships_section(relationships):
    relationships_section = []
    for rel in relationships:
        relationships_section.append({
            'source': rel['source'],
            'target': rel['target']
        })
    return relationships_section

def convert_mmd_to_yaml(mmd_content):
    entities, validations, relationships = parse_mmd(mmd_content)
    processed_entities = process_entities(entities, validations)
    processed_entities = map_relationships(processed_entities, relationships)
    relationships_section = build_relationships_section(relationships)

    # Combine into final YAML structure
    yaml_output = {}
    yaml_output['_relationships'] = relationships_section
    for entity, data in processed_entities.items():
        yaml_output[entity] = data

    return yaml.dump(yaml_output, sort_keys=False)

def main():
    try:
        # Read MMD content from 'schema.mmd' file
        with open('schema.mmd', 'r') as file:
            mmd_content = file.read()
    except FileNotFoundError:
        print("Error: 'schema.mmd' file not found. Please ensure the file exists in the current directory.")
        return

    yaml_result = convert_mmd_to_yaml(mmd_content)

    # Write the YAML to 'schema.yaml'
    with open('schema.yaml', 'w') as yaml_file:
        yaml_file.write(yaml_result)
    print("YAML conversion completed. Check 'schema.yaml'.")

if __name__ == "__main__":
    main()
