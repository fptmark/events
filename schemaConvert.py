import re
import yaml
from collections import defaultdict

def parse_validation_string(validation_str):
    """
    Parses a validation string like "{ type ObjectId, required true, autoGenerate true }"
    or "{ type: ObjectId, required: true }" into a Python dictionary.
    """
    validation = {}
    # Remove the surrounding braces and whitespace
    validation_str = validation_str.strip().strip('{}').strip()
    # Split by commas that are not inside brackets (for now, we assume no nested commas)
    pairs = re.split(r'\s*,\s*', validation_str)
    
    for pair in pairs:
        if not pair:
            continue
        # Try splitting by colon; if not found, split by whitespace
        if ':' in pair:
            key, value = pair.split(':', 1)
        else:
            parts = pair.split(None, 1)
            if len(parts) != 2:
                continue
            key, value = parts
        key = key.strip()
        value = value.strip()
        # Handle booleans
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False

        value_str = value if isinstance(value, str) else str(value)

        # Handle list values (e.g., enums or arrays) if wrapped in [ ]
        if value_str.startswith('[') and value_str.endswith(']'):
            items = re.findall(r"'([^']*)'|\"([^\"]*)\"|([^,\s]+)", value_str[1:-1])
            items = [item[0] or item[1] or item[2] for item in items]
            value = items
        else:
            # Remove any surrounding quotes
            value = value_str.strip('\'"')
        validation[key] = value
    return validation

def parse_mmd(mmd_content):
    entities = {}
    validations = {}
    relationships = []
    lines = mmd_content.splitlines()
    current_entity = None
    last_entity = None
    validation_entity = None

    # Regular expressions
    entity_pattern = re.compile(r'^(\w+)\s*\{')
    field_pattern = re.compile(r'^\s*(\w+)\s+([\w\[\]]+)')
    validation_start_pattern = re.compile(r'^%%\s*@validation\s+(\w+)')
    # Allow optional colon after field name: (\w+):?\s*\{(.+)\}
    validation_field_pattern = re.compile(r'^%%\s+(\w+):?\s*\{(.+)\}')
    inherits_pattern = re.compile(r'^%%\s*@inherits\s+(\w+)')
    relationship_pattern = re.compile(r'^(\w+)\s+\|\|--o\{\s*(\w+):.*$')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('erDiagram'):
            continue

        # Check for entity definition
        entity_match = entity_pattern.match(line)
        if entity_match:
            current_entity = entity_match.group(1)
            last_entity = current_entity
            entities[current_entity] = {'fields': {}, 'relations': []}
            continue

        # Check for end of entity block
        if line == '}':
            current_entity = None
            continue

        # Check for validation start
        validation_start_match = validation_start_pattern.match(line)
        if validation_start_match:
            validation_entity = validation_start_match.group(1)
            validations[validation_entity] = {}
            continue

        # Check for @inherits line
        inherits_match = inherits_pattern.match(line)
        if inherits_match:
            parent = inherits_match.group(1)
            # Associate with the last defined entity
            if last_entity:
                entities[last_entity]['inherits'] = parent
            continue

        # Check for validation fields
        validation_field_match = validation_field_pattern.match(line)
        if validation_field_match and validation_entity:
            field_name = validation_field_match.group(1)
            field_validations_str = validation_field_match.group(2)
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
                # In our ER syntax, the first token is the type and the second is the field name.
                field_type = field_match.group(1)
                field_name = field_match.group(2)
                entities[current_entity]['fields'][field_name] = {'type': field_type}
    return entities, validations, relationships

def process_entities(entities, validations):
    processed = {}
    for entity, data in entities.items():
        entity_key = entity
        processed[entity_key] = {'fields': {}, 'relations': []}
        # If this entity inherits from another, record it.
        if 'inherits' in data:
            processed[entity_key]['inherits'] = data['inherits']
        fields = data['fields']
        entity_validations = validations.get(entity, {})
        for field, details in fields.items():
            field_info = {}
            field_type = details['type']
            # Handle Array types (if using Array[...] syntax)
            array_match = re.match(r'Array\[(\w+)\]', field_type)
            if array_match:
                base_type = array_match.group(1)
                field_info['type'] = f"Array[{base_type}]"
            else:
                field_info['type'] = field_type
            # Add validation data if present
            validation = entity_validations.get(field, {})
            required = validation.get('required', False)
            if isinstance(required, bool):
                required = 'True' if required else 'False'
            else:
                required = 'True' if str(required).lower() == 'true' else 'False'
            field_info['required'] = required
            for key, value in validation.items():
                if key != 'required':
                    field_info[key] = value
            processed[entity_key]['fields'][field] = field_info
        processed[entity_key]['relations'] = []  # To be filled later
        print(f"Processed Entity: {entity_key}")  # Debug statement
    return processed

def map_relationships(processed_entities, relationships):
    for rel in relationships:
        source = rel['source']
        target = rel['target']
        if source in processed_entities:
            processed_entities[source]['relations'].append(target)
            print(f"Mapped Relationship: {source} -> {target}")  # Debug statement
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
        # Read MMD content from 'schema.mmd'
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
