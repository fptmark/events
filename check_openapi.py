#!/usr/bin/env python3
"""
Quick script to check OpenAPI schema for GET endpoints
"""

import requests
import json

SERVER_URL = "http://127.0.0.1:5500"

def check_openapi_schema():
    try:
        response = requests.get(f"{SERVER_URL}/openapi.json", timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to fetch OpenAPI schema: {response.status_code}")
            return

        schema = response.json()
        
        # Check GET /api/user endpoint
        user_list_path = schema.get("paths", {}).get("/api/user", {}).get("get", {})
        if user_list_path:
            response_schema = user_list_path.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
            print("📋 GET /api/user response schema:")
            print(json.dumps(response_schema, indent=2))
            
            # Check if it references the correct response model
            ref = response_schema.get("$ref")
            if ref:
                print(f"\n🔗 References: {ref}")
        
        # Check GET /api/user/{id} endpoint  
        user_get_path = schema.get("paths", {}).get("/api/user/{entity_id}", {}).get("get", {})
        if user_get_path:
            response_schema = user_get_path.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
            print("\n📄 GET /api/user/{id} response schema:")
            print(json.dumps(response_schema, indent=2))
            
            # Check if it references the correct response model
            ref = response_schema.get("$ref")
            if ref:
                print(f"\n🔗 References: {ref}")
        
        # Check User schema
        user_schema = schema.get("components", {}).get("schemas", {}).get("User", {})
        if user_schema:
            properties = user_schema.get("properties", {})
            
            print("\n👤 User schema dob field:")
            print(json.dumps(properties.get("dob", {}), indent=2))
            
            print("\n🔤 User schema gender field:")  
            print(json.dumps(properties.get("gender", {}), indent=2))
            
        # List all response models
        schemas = schema.get("components", {}).get("schemas", {})
        response_models = [name for name in schemas.keys() if "Response" in name]
        print(f"\n📊 Available response models: {response_models}")
        
    except Exception as e:
        print(f"❌ Error checking OpenAPI schema: {e}")

if __name__ == "__main__":
    check_openapi_schema()