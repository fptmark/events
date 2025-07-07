#!/usr/bin/env python3
"""
Analyze OpenAPI spec for User model issues
"""

import requests
import json

SERVER_URL = "http://127.0.0.1:5500"

def analyze_user_schemas():
    try:
        response = requests.get(f"{SERVER_URL}/openapi.json", timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to fetch OpenAPI: {response.status_code}")
            return

        schema = response.json()
        components = schema.get("components", {}).get("schemas", {})
        
        print("🔍 ANALYZING USER MODEL SCHEMAS")
        print("=" * 50)
        
        # Check what User schemas exist
        user_schemas = [name for name in components.keys() if 'User' in name]
        print(f"📋 Found User schemas: {user_schemas}")
        
        for schema_name in ['User', 'UserCreate', 'UserUpdate']:
            if schema_name in components:
                print(f"\n📄 {schema_name} Schema:")
                user_schema = components[schema_name]
                properties = user_schema.get("properties", {})
                
                # Check dob field
                if "dob" in properties:
                    dob_field = properties["dob"]
                    print(f"  📅 dob: {json.dumps(dob_field, indent=4)}")
                else:
                    print("  ❌ dob field missing")
                
                # Check gender field  
                if "gender" in properties:
                    gender_field = properties["gender"]
                    print(f"  👤 gender: {json.dumps(gender_field, indent=4)}")
                else:
                    print("  ❌ gender field missing")
                
                # Check netWorth field
                if "netWorth" in properties:
                    networth_field = properties["netWorth"]
                    print(f"  💰 netWorth: {json.dumps(networth_field, indent=4)}")
                else:
                    print("  ❌ netWorth field missing")
                    
                # Check required fields
                required = user_schema.get("required", [])
                print(f"  📝 Required fields: {required}")
                
            else:
                print(f"\n❌ {schema_name} schema missing")
        
        # Check endpoint schemas
        paths = schema.get("paths", {})
        user_endpoints = {path: methods for path, methods in paths.items() if '/user' in path}
        
        print(f"\n🛣️  USER ENDPOINTS:")
        for path, methods in user_endpoints.items():
            print(f"  {path}:")
            for method, details in methods.items():
                if 'responses' in details:
                    response_200 = details.get('responses', {}).get('200', {})
                    content = response_200.get('content', {}).get('application/json', {})
                    response_schema = content.get('schema', {})
                    ref = response_schema.get('$ref', 'No $ref')
                    print(f"    {method.upper()}: {ref}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_user_schemas()