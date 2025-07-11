#!/usr/bin/env python3
"""
Standalone OpenAPI generator that imports models directly.
No dependency on main.py, FastAPI, or database configurations.
"""

import sys
import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add the app to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import models directly - minimal dependencies
from app.models.account_model import Account
from app.models.user_model import User
from app.models.profile_model import Profile
from app.models.tagaffinity_model import TagAffinity
from app.models.event_model import Event
from app.models.userevent_model import UserEvent
from app.models.url_model import Url
from app.models.crawl_model import Crawl


class StandaloneOpenAPIGenerator:
    """Generate OpenAPI 3.0 specification from model metadata directly"""
    
    def __init__(self):
        self.openapi_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "Events Management API",
                "description": "Comprehensive API documentation generated from schema metadata",
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": "http://localhost:5500/api",
                    "description": "Development server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "responses": {},
                "parameters": {},
                "securitySchemes": {
                    "cookieAuth": {
                        "type": "apiKey",
                        "in": "cookie",
                        "name": "session"
                    }
                }
            }
        }
        
        # Entity models mapping
        self.entity_models = {
            "Account": Account,
            "User": User,
            "Profile": Profile,
            "TagAffinity": TagAffinity,
            "Event": Event,
            "UserEvent": UserEvent,
            "Url": Url,
            "Crawl": Crawl
        }
    
    def generate(self) -> Dict[str, Any]:
        """Generate complete OpenAPI specification"""
        print("🚀 Generating OpenAPI specification from models...")
        
        # Generate schemas for all entities
        for entity_name, model_class in self.entity_models.items():
            print(f"   📄 Processing {entity_name}...")
            entity_meta = model_class.get_metadata()
            self._generate_entity_schemas(entity_name, entity_meta)
            self._generate_entity_paths(entity_name, entity_meta)
        
        # Add common response schemas
        self._generate_common_schemas()
        
        return self.openapi_spec
    
    def _generate_entity_schemas(self, entity_name: str, entity_meta: Dict[str, Any]):
        """Generate schemas for an entity (read, create, update models)"""
        
        # Main entity schema (for responses)
        main_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Create schema (no id, auto-generated fields)
        create_schema = {
            "type": "object", 
            "properties": {},
            "required": []
        }
        
        # Update schema (all optional except constraints)
        update_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Process each field
        for field_name, field_meta in entity_meta.get("fields", {}).items():
            field_schema = self._convert_field_to_openapi(field_name, field_meta)
            
            # Add to main schema
            main_schema["properties"][field_name] = field_schema
            if field_meta.get("required"):
                main_schema["required"].append(field_name)
            
            # Add to create schema (skip auto-generated fields and id)
            if not field_meta.get("autoGenerate") and field_name != "id":
                create_schema["properties"][field_name] = field_schema.copy()
                if field_meta.get("required"):
                    create_schema["required"].append(field_name)
            
            # Add to update schema (all optional, skip auto-update fields)
            if not field_meta.get("autoUpdate"):
                update_field = field_schema.copy()
                # Make all update fields optional
                if "required" in update_field:
                    del update_field["required"]
                update_schema["properties"][field_name] = update_field
        
        # Add entity description from UI metadata
        ui_meta = entity_meta.get("ui", {})
        description = ui_meta.get("description", f"{entity_name} entity")
        
        main_schema["description"] = description
        create_schema["description"] = f"Create {entity_name} request"
        update_schema["description"] = f"Update {entity_name} request"
        
        # Store schemas
        self.openapi_spec["components"]["schemas"][entity_name] = main_schema
        self.openapi_spec["components"]["schemas"][f"{entity_name}Create"] = create_schema
        self.openapi_spec["components"]["schemas"][f"{entity_name}Update"] = update_schema
    
    def _convert_field_to_openapi(self, field_name: str, field_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a field metadata to OpenAPI schema"""
        field_type = field_meta.get("type", "String")
        
        # Base schema
        schema = {}
        
        # Type mapping
        type_mapping = {
            "String": {"type": "string"},
            "Integer": {"type": "integer"},
            "Number": {"type": "number"},
            "Boolean": {"type": "boolean"},
            "Currency": {"type": "number", "format": "currency"},
            "ISODate": {"type": "string", "format": "date-time"},
            "ObjectId": {"type": "string", "format": "objectid"},
            "Array[String]": {"type": "array", "items": {"type": "string"}}
        }
        
        schema.update(type_mapping.get(field_type, {"type": "string"}))
        
        # Add validation constraints
        if "min_length" in field_meta:
            schema["minLength"] = field_meta["min_length"]
        if "max_length" in field_meta:
            schema["maxLength"] = field_meta["max_length"]
        if "ge" in field_meta:
            schema["minimum"] = field_meta["ge"]
        if "le" in field_meta:
            schema["maximum"] = field_meta["le"]
        
        # Pattern validation
        if "pattern" in field_meta and "regex" in field_meta["pattern"]:
            schema["pattern"] = field_meta["pattern"]["regex"]
        
        # Enum values
        if "enum" in field_meta and "values" in field_meta["enum"]:
            schema["enum"] = field_meta["enum"]["values"]
        
        # Description from UI metadata or generate generically
        ui_meta = field_meta.get("ui", {})
        if "displayName" in ui_meta:
            schema["description"] = ui_meta["displayName"]
        else:
            # Generate generic description based on type and attributes
            if field_meta.get("autoGenerate"):
                schema["description"] = f"Auto-generated {field_type.lower()} field"
            elif field_meta.get("autoUpdate"):
                schema["description"] = f"Auto-updated {field_type.lower()} field"
            elif field_type == "ISODate":
                schema["description"] = "Date and time in ISO format"
            elif field_type == "ObjectId":
                schema["description"] = "Reference to another entity"
            elif field_type == "Currency":
                schema["description"] = "Monetary value"
            elif field_type == "Boolean":
                schema["description"] = "True or false value"
            elif "enum" in field_meta:
                values = field_meta["enum"].get("values", [])
                schema["description"] = f"One of: {', '.join(values)}"
            else:
                schema["description"] = f"{field_type} field"
        
        # Add examples based on field type and name
        schema["example"] = self._generate_field_example(field_name, field_meta)
        
        return schema
    
    def _generate_field_example(self, field_name: str, field_meta: Dict[str, Any]) -> Any:
        """Generate example values for fields based on type and patterns"""
        field_type = field_meta.get("type", "String")
        
        # Type-based examples (generic, no field name dependencies)
        if field_type == "String":
            # Check for enum first
            if "enum" in field_meta and "values" in field_meta["enum"]:
                return field_meta["enum"]["values"][0]
            
            # Check for email pattern
            if "pattern" in field_meta and "regex" in field_meta["pattern"]:
                regex = field_meta["pattern"]["regex"]
                if "@" in regex:
                    return "user@example.com"
                elif "^https?://" in regex:
                    return "https://example.com"
            
            # Use length constraints for generic string
            min_len = field_meta.get("min_length", 3)
            max_len = field_meta.get("max_length", 20)
            example_len = min(max(min_len, 8), max_len)
            return "example" + "x" * (example_len - 7) if example_len > 7 else "example"[:example_len]
        
        elif field_type == "Integer":
            min_val = field_meta.get("ge", 1)
            max_val = field_meta.get("le", 100)
            return min(max(min_val, 42), max_val)
        
        elif field_type == "Number":
            min_val = field_meta.get("ge", 1.0)
            max_val = field_meta.get("le", 1000.0) 
            return min(max(min_val, 123.45), max_val)
        
        elif field_type == "Currency":
            min_val = field_meta.get("ge", 0.0)
            max_val = field_meta.get("le", 10000.0)
            return min(max(min_val, 1000.00), max_val)
        
        elif field_type == "Boolean":
            return True
        
        elif field_type == "ISODate":
            return "2024-01-01T12:00:00Z"
        
        elif field_type == "ObjectId":
            return "507f1f77bcf86cd799439011"
        
        elif field_type == "Array[String]":
            return ["item1", "item2"]
        
        return "example"
    
    def _generate_entity_paths(self, entity_name: str, entity_meta: Dict[str, Any]):
        """Generate API paths for an entity"""
        entity_lower = entity_name.lower()
        operations = entity_meta.get("operations", "crud")
        
        # Collection paths (/api/users)
        collection_path = f"/{entity_lower}"
        self.openapi_spec["paths"][collection_path] = {}
        
        # GET collection (list)
        if "r" in operations:
            self.openapi_spec["paths"][collection_path]["get"] = {
                "summary": f"List {entity_name}s",
                "description": f"Retrieve all {entity_name.lower()} entities",
                "tags": [entity_name],
                "responses": {
                    "200": {
                        "description": f"List of {entity_name.lower()}s retrieved successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{entity_name}ListResponse"}
                            }
                        }
                    },
                    "500": {"$ref": "#/components/responses/InternalServerError"}
                }
            }
        
        # POST collection (create)
        if "c" in operations:
            self.openapi_spec["paths"][collection_path]["post"] = {
                "summary": f"Create {entity_name}",
                "description": f"Create a new {entity_name.lower()} entity",
                "tags": [entity_name],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{entity_name}Create"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": f"{entity_name} created successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{entity_name}Response"}
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/ValidationError"},
                    "409": {"$ref": "#/components/responses/DuplicateError"},
                    "500": {"$ref": "#/components/responses/InternalServerError"}
                }
            }
        
        # Item paths (/api/users/{id})
        item_path = f"/{entity_lower}/{{id}}"
        self.openapi_spec["paths"][item_path] = {}
        
        # GET item
        if "r" in operations:
            self.openapi_spec["paths"][item_path]["get"] = {
                "summary": f"Get {entity_name}",
                "description": f"Retrieve a specific {entity_name.lower()} by ID",
                "tags": [entity_name],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "objectid"},
                        "description": f"{entity_name} ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": f"{entity_name} retrieved successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{entity_name}Response"}
                            }
                        }
                    },
                    "404": {"$ref": "#/components/responses/NotFoundError"},
                    "500": {"$ref": "#/components/responses/InternalServerError"}
                }
            }
        
        # PUT item (update)
        if "u" in operations:
            self.openapi_spec["paths"][item_path]["put"] = {
                "summary": f"Update {entity_name}",
                "description": f"Update a specific {entity_name.lower()} by ID",
                "tags": [entity_name],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "objectid"},
                        "description": f"{entity_name} ID"
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{entity_name}Update"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": f"{entity_name} updated successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{entity_name}Response"}
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/ValidationError"},
                    "404": {"$ref": "#/components/responses/NotFoundError"},
                    "409": {"$ref": "#/components/responses/DuplicateError"},
                    "500": {"$ref": "#/components/responses/InternalServerError"}
                }
            }
        
        # DELETE item
        if "d" in operations:
            self.openapi_spec["paths"][item_path]["delete"] = {
                "summary": f"Delete {entity_name}",
                "description": f"Delete a specific {entity_name.lower()} by ID",
                "tags": [entity_name],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "objectid"},
                        "description": f"{entity_name} ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": f"{entity_name} deleted successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DeleteResponse"}
                            }
                        }
                    },
                    "404": {"$ref": "#/components/responses/NotFoundError"},
                    "500": {"$ref": "#/components/responses/InternalServerError"}
                }
            }
        
        # Generate response schemas for this entity
        self._generate_entity_response_schemas(entity_name)
    
    def _generate_entity_response_schemas(self, entity_name: str):
        """Generate response wrapper schemas for an entity"""
        
        # Single entity response
        self.openapi_spec["components"]["schemas"][f"{entity_name}Response"] = {
            "type": "object",
            "properties": {
                "data": {"$ref": f"#/components/schemas/{entity_name}"},
                "message": {"type": "string", "nullable": True},
                "level": {"type": "string", "enum": ["success", "info", "warning", "error"], "nullable": True},
                "notifications": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/Notification"}
                },
                "summary": {"$ref": "#/components/schemas/NotificationSummary"}
            },
            "description": f"Response containing a single {entity_name}"
        }
        
        # List response
        self.openapi_spec["components"]["schemas"][f"{entity_name}ListResponse"] = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"$ref": f"#/components/schemas/{entity_name}"}
                },
                "message": {"type": "string", "nullable": True},
                "level": {"type": "string", "enum": ["success", "info", "warning", "error"], "nullable": True},
                "notifications": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/Notification"}
                },
                "summary": {"$ref": "#/components/schemas/NotificationSummary"}
            },
            "description": f"Response containing a list of {entity_name}s"
        }
    
    def _generate_common_schemas(self):
        """Generate common schemas used across all endpoints"""
        
        # Notification schema
        self.openapi_spec["components"]["schemas"]["Notification"] = {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "level": {"type": "string", "enum": ["success", "info", "warning", "error"]},
                "type": {"type": "string", "enum": ["validation", "database", "business", "system", "security"]},
                "entity": {"type": "string", "nullable": True},
                "operation": {"type": "string", "nullable": True},
                "field": {"type": "string", "nullable": True},
                "value": {"nullable": True},
                "entity_id": {"type": "string", "nullable": True},
                "timestamp": {"type": "string", "format": "date-time"}
            }
        }
        
        # Notification summary
        self.openapi_spec["components"]["schemas"]["NotificationSummary"] = {
            "type": "object",
            "properties": {
                "total_entities": {"type": "integer"},
                "perfect": {"type": "integer"},
                "successful": {"type": "integer"},
                "warnings": {"type": "integer"},
                "errors": {"type": "integer"}
            }
        }
        
        # Delete response
        self.openapi_spec["components"]["schemas"]["DeleteResponse"] = {
            "type": "object",
            "properties": {
                "data": {"type": "boolean"},
                "message": {"type": "string"},
                "level": {"type": "string", "enum": ["success"]}
            }
        }
        
        # Error response schemas
        self.openapi_spec["components"]["responses"]["ValidationError"] = {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "data": {"nullable": True},
                            "message": {"type": "string"},
                            "level": {"type": "string", "enum": ["error"]},
                            "notifications": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Notification"}
                            }
                        }
                    }
                }
            }
        }
        
        self.openapi_spec["components"]["responses"]["NotFoundError"] = {
            "description": "Resource not found",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "data": {"nullable": True},
                            "message": {"type": "string"},
                            "level": {"type": "string", "enum": ["error"]}
                        }
                    }
                }
            }
        }
        
        self.openapi_spec["components"]["responses"]["DuplicateError"] = {
            "description": "Duplicate resource error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "data": {"nullable": True},
                            "message": {"type": "string"},
                            "level": {"type": "string", "enum": ["error"]},
                            "notifications": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/Notification"}
                            }
                        }
                    }
                }
            }
        }
        
        self.openapi_spec["components"]["responses"]["InternalServerError"] = {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "data": {"nullable": True},
                            "message": {"type": "string"},
                            "level": {"type": "string", "enum": ["error"]}
                        }
                    }
                }
            }
        }


def main():
    """Generate OpenAPI specification and save to file"""
    try:
        print("🚀 Standalone OpenAPI Generator")
        print("📦 Dependencies: Models only (no config, no FastAPI, no DB)")
        
        generator = StandaloneOpenAPIGenerator()
        spec = generator.generate()
        
        # Save to file
        output_file = Path("openapi.json")
        with open(output_file, 'w') as f:
            json.dump(spec, f, indent=2)
        
        print(f"\n✅ OpenAPI specification generated successfully!")
        print(f"📄 Saved to: {output_file.absolute()}")
        print(f"📊 Generated {len(spec['components']['schemas'])} schemas")
        print(f"🛣️  Generated {len(spec['paths'])} API paths")
        
        # Show summary
        entities = [name for name in spec['components']['schemas'].keys() 
                   if not name.endswith(('Response', 'Create', 'Update')) 
                   and name not in ['Notification', 'NotificationSummary', 'DeleteResponse']]
        print(f"🏗️  Entities: {', '.join(entities)}")
        
        print(f"\n🌐 View documentation at: http://localhost:5500/docs")
        print(f"📋 Raw spec available at: http://localhost:5500/openapi.json")
        
    except Exception as e:
        print(f"❌ Error generating OpenAPI specification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()