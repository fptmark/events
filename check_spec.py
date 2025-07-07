#!/usr/bin/env python3
import requests
import json

try:
    response = requests.get("http://127.0.0.1:5500/openapi.json", timeout=10)
    if response.status_code == 200:
        schema = response.json()
        components = schema.get("components", {}).get("schemas", {})
        
        print("USER SCHEMAS FOUND:")
        user_schemas = [name for name in components.keys() if 'User' in name]
        print(f"Schemas: {user_schemas}")
        
        for schema_name in ['User', 'UserCreate', 'UserUpdate']:
            if schema_name in components:
                print(f"\n=== {schema_name} ===")
                user_schema = components[schema_name]
                properties = user_schema.get("properties", {})
                required = user_schema.get("required", [])
                
                # Check critical fields
                for field_name in ['dob', 'gender', 'netWorth']:
                    if field_name in properties:
                        field_def = properties[field_name]
                        print(f"{field_name}: {json.dumps(field_def, indent=2)}")
                    else:
                        print(f"{field_name}: MISSING")
                
                print(f"Required: {required}")
            else:
                print(f"\n❌ {schema_name} MISSING")
    else:
        print(f"❌ HTTP {response.status_code}: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")