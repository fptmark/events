import re
import yaml


def parse_validation_rules(rules):
    """
    Safely converts a non-JSON-like validation rules string into a Python dictionary.
    Handles regex patterns and array-like types.
    """
    # Replace true/false with Python True/False
    rules = rules.replace("true", "True").replace("false", "False")

    # Quote unquoted terms (e.g., ObjectId, Array[String]) and regex patterns
    rules = re.sub(r"(?<=:\s)([a-zA-Z][\w\[\]]*)", r"'\1'", rules)
    rules = re.sub(r"pattern:\s([^,}]+)", r"pattern: '\1'", rules)

    # Safely parse as a dictionary using yaml
    try:
        return yaml.safe_load(rules)
    except yaml.YAMLError:
        raise ValueError(f"Invalid validation rules: {rules}")


def parse_enhanced_mmd(file_path):
    """Parses the enhanced MMD file to extract schema, validation metadata, and relationships."""
    entities = {}
    relationships = []  # Global list of all relationships
    current_entity = None
    in_validation = False

    with open(file_path, "r") as file:
        lines = file.readlines()

    for line in lines:
        line = line.strip()

        # Detect and parse relationship definitions
        relationship_match = re.match(r"(\w+)\s+(\|\|--o{\s+\w+: \"\")", line)
        if relationship_match:
            source, relation = line.split("||--o{")
            source = source.strip()
            target = relation.split(":")[0].strip()
            relationships.append({"source": source, "target": target})
            # Add relationships to the source entity
            if source in entities:
                entities[source].setdefault("relations", []).append(target)
            continue

        # Detect entity definition
        entity_match = re.match(r"(\w+)\s+{", line)
        if entity_match:
            current_entity = entity_match.group(1)
            entities[current_entity] = {"fields": {}, "validation": {}, "relations": []}
            in_validation = False  # Reset validation flag
            continue

        # Detect field definitions
        if current_entity and "}" not in line and not line.startswith("%%"):
            field_definition = line.split()
            if len(field_definition) >= 2:
                field_type = field_definition[0]
                field_name = field_definition[1]
                entities[current_entity]["fields"][field_name] = {"type": field_type}
            continue

        # Detect validation metadata
        validation_match = re.match(r"%%\s+@validation\s+(\w+)", line)
        if validation_match:
            in_validation = True
            current_entity = validation_match.group(1)
            continue

        # Parse validation rules
        if in_validation and line.startswith("%%") and ":" in line:
            field, rules = line[2:].split(": ", 1)
            try:
                rules_dict = parse_validation_rules(rules)
                entities[current_entity]["validation"][field.strip()] = rules_dict
            except ValueError:
                print(f"Failed to parse validation rules for '{field.strip()}' in '{current_entity}': {rules}")

    return entities, relationships


def generate_yaml(parsed_entities, relationships, yaml_file_path):
    """Generates YAML from parsed MMD schema, validation rules, and relationships."""
    yaml_data = {}

    for entity_name, entity_data in parsed_entities.items():
        combined_fields = {}
        for field_name, field_type in entity_data["fields"].items():
            combined_fields[field_name] = field_type.copy()
            if field_name in entity_data["validation"]:
                combined_fields[field_name].update(entity_data["validation"][field_name])
        yaml_data[entity_name] = {
            "fields": combined_fields,
            "relations": entity_data["relations"],  # Add relations for the entity
        }

    # Optionally store global relationships (not strictly needed if they're per-entity)
    yaml_data["_relationships"] = relationships

    # Write to YAML
    with open(yaml_file_path, "w") as yaml_file:
        yaml.dump(yaml_data, yaml_file, default_flow_style=False)
    print(f"YAML schema saved to {yaml_file_path}")


def main():
    mmd_file = "schema.mmd"  # Input MMD file
    yaml_file = "schema.yaml"  # Output YAML file

    parsed_entities, relationships = parse_enhanced_mmd(mmd_file)
    generate_yaml(parsed_entities, relationships, yaml_file)


if __name__ == "__main__":
    main()

