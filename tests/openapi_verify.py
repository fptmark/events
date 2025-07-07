#!/usr/bin/env python3
"""
Complete verification of OpenAPI spec - both endpoints and schemas
"""

import requests
import json

SERVER_URL = "http://127.0.0.1:5500"

def verify_complete():
    try:
        response = requests.get(f"{SERVER_URL}/openapi.json", timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to fetch OpenAPI: {response.status_code}")
            return

        schema = response.json()
        
        print("🔍 COMPLETE OPENAPI VERIFICATION")
        print("=" * 60)
        
        # 1. CHECK ENDPOINTS
        print("\n📡 CHECKING ENDPOINTS:")
        paths = schema.get("paths", {})
        user_endpoints = {path: methods for path, methods in paths.items() if '/user' in path}
        
        for path, methods in user_endpoints.items():
            print(f"\n  📍 {path}:")
            for method, details in methods.items():
                method_upper = method.upper()
                
                # Check request body for POST/PUT
                if method in ['post', 'put']:
                    request_body = details.get('requestBody', {})
                    content = request_body.get('content', {}).get('application/json', {})
                    req_schema = content.get('schema', {}).get('$ref', 'No schema')
                    print(f"    {method_upper} request: {req_schema}")
                
                # Check response schema
                if 'responses' in details:
                    response_200 = details.get('responses', {}).get('200', {})
                    content = response_200.get('content', {}).get('application/json', {})
                    resp_schema = content.get('schema', {}).get('$ref', 'No schema')
                    print(f"    {method_upper} response: {resp_schema}")
        
        # 2. CHECK SCHEMAS
        print("\n📋 CHECKING SCHEMAS:")
        components = schema.get("components", {}).get("schemas", {})
        user_schemas = [name for name in components.keys() if 'User' in name]
        print(f"  Found schemas: {user_schemas}")
        
        # Check each User schema
        for schema_name in ['User', 'UserCreate', 'UserUpdate']:
            if schema_name in components:
                print(f"\n  📄 {schema_name} Schema:")
                user_schema = components[schema_name]
                properties = user_schema.get("properties", {})
                required = user_schema.get("required", [])
                
                print(f"    Required fields: {required}")
                
                # Check dob field
                if "dob" in properties:
                    dob_field = properties["dob"]
                    print(f"    📅 dob: {json.dumps(dob_field, indent=6)}")
                else:
                    print("    ❌ dob field MISSING")
                
                # Check gender field  
                if "gender" in properties:
                    gender_field = properties["gender"]
                    print(f"    👤 gender: {json.dumps(gender_field, indent=6)}")
                else:
                    print("    ❌ gender field MISSING")
                
                # Check netWorth field
                if "netWorth" in properties:
                    networth_field = properties["netWorth"]
                    print(f"    💰 netWorth: {json.dumps(networth_field, indent=6)}")
                else:
                    print("    ❌ netWorth field MISSING")
                    
            else:
                print(f"\n  ❌ {schema_name} schema MISSING")
        
        # 3. SUMMARY CHECK
        print(f"\n📊 SUMMARY:")
        print(f"  Total endpoints: {len(user_endpoints)}")
        print(f"  Total User schemas: {len(user_schemas)}")
        
        # Expected: 4 endpoints (GET, GET/{id}, POST, PUT/{id}) and 3 schemas (User, UserCreate, UserUpdate)
        if len(user_endpoints) >= 2 and len(user_schemas) == 3:
            print("  ✅ Basic structure looks correct")
        else:
            print(f"  ❌ Structure issue - Expected ~4 endpoints and 3 schemas")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_complete()