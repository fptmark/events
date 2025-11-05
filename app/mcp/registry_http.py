"""
HTTP-based MCP tool registry.
Fetches metadata from REST API and generates tools dynamically.
No dependencies on Python model classes - pure HTTP client.
"""
from typing import Any, Dict, List, Callable
import logging
import httpx

from app.core.config import Config

logger = logging.getLogger(__name__)


class HTTPToolRegistry:
    """
    Tool registry that uses REST API exclusively.
    Fetches metadata from /api/metadata and makes HTTP calls for all operations.
    """

    def __init__(self):
        """Initialize HTTP-based tool registry."""
        # Get REST API base URL from config
        server_port = Config.get('server_port', 5500)
        self.api_base_url = f"http://localhost:{server_port}/api"
        logger.info(f"MCP server will call REST API at: {self.api_base_url}")

        self.metadata = None
        self._tools = []

    async def initialize(self):
        """Fetch metadata from REST API"""
        logger.info("Fetching metadata from REST API...")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_base_url}/metadata")
            response.raise_for_status()
            self.metadata = response.json()

        entities = self.metadata.get("entities", {})
        logger.info(f"Loaded metadata for {len(entities)} entities: {list(entities.keys())}")

        # Generate tools for each entity
        for entity_name in entities.keys():
            self._register_entity_tools(entity_name)

    def _register_entity_tools(self, entity: str):
        """Register CRUD tools for an entity"""
        # List tool
        self._tools.append({
            "name": f"list_{entity.lower()}",
            "description": f"List {entity} records with pagination, sorting, and filtering",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "description": "Page number (default: 1)"},
                    "pageSize": {"type": "integer", "description": "Records per page (default: 50)"},
                    "sort_by": {"type": "string", "description": "Sort field (prefix with - for desc)"},
                    "filter_field": {"type": "string", "description": "Field to filter on"},
                    "filter_value": {"type": "string", "description": "Filter value"},
                    "substring_match": {"type": "string", "description": "Set to 'full' for exact match. Omit for substring matching (default).", "enum": ["full"]}
                }
            },
            "handler": self._create_list_handler(entity)
        })

        # Get tool
        self._tools.append({
            "name": f"get_{entity.lower()}",
            "description": f"Get a single {entity} record by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": f"{entity} ID"}
                },
                "required": ["id"]
            },
            "handler": self._create_get_handler(entity)
        })

        # Create tool
        self._tools.append({
            "name": f"create_{entity.lower()}",
            "description": f"Create a new {entity} record",
            "inputSchema": self._build_create_schema(entity),
            "handler": self._create_create_handler(entity)
        })

        # Update tool
        self._tools.append({
            "name": f"update_{entity.lower()}",
            "description": f"Update an existing {entity} record (partial update supported)",
            "inputSchema": self._build_update_schema(entity),
            "handler": self._create_update_handler(entity)
        })

        # Delete tool
        self._tools.append({
            "name": f"delete_{entity.lower()}",
            "description": f"Delete a {entity} record by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": f"{entity} ID"}
                },
                "required": ["id"]
            },
            "handler": self._create_delete_handler(entity)
        })

    def _build_create_schema(self, entity: str) -> Dict[str, Any]:
        """Build JSON schema for create operation from metadata"""
        entity_meta = self.metadata["entities"][entity]
        fields = entity_meta.get("fields", {})

        properties = {}
        required = []

        for field_name, field_meta in fields.items():
            # Skip auto-generated fields
            if field_name == "id" or field_meta.get("autoGenerate"):
                continue

            properties[field_name] = self._field_to_json_schema(field_meta)

            if field_meta.get("required"):
                required.append(field_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def _build_update_schema(self, entity: str) -> Dict[str, Any]:
        """Build JSON schema for update operation from metadata"""
        entity_meta = self.metadata["entities"][entity]
        fields = entity_meta.get("fields", {})

        properties = {"id": {"type": "string", "description": f"{entity} ID"}}

        for field_name, field_meta in fields.items():
            # Skip id and auto-generated fields
            if field_name == "id" or field_meta.get("autoGenerate"):
                continue

            properties[field_name] = self._field_to_json_schema(field_meta)

        return {
            "type": "object",
            "properties": properties,
            "required": ["id"]  # Only ID is required for update
        }

    def _field_to_json_schema(self, field_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Convert field metadata to JSON schema property"""
        field_type = field_meta.get("type", "String")

        # Map API types to JSON schema types
        type_map = {
            "String": "string",
            "Integer": "integer",
            "Float": "number",
            "Number": "number",
            "Currency": "number",
            "Boolean": "boolean",
            "Date": "string",
            "Datetime": "string",
            "ObjectId": "string",
            "Array": "array",
            "Array[String]": "array"
        }

        json_type = type_map.get(field_type, "string")
        schema = {"type": json_type}

        # Add enum if present
        if "enum" in field_meta and "values" in field_meta["enum"]:
            schema["enum"] = field_meta["enum"]["values"]

        # Add description from UI metadata
        ui_meta = field_meta.get("ui", {})
        if "displayName" in ui_meta:
            schema["description"] = ui_meta["displayName"]

        return schema

    def _format_error_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format unified notification structure into user-friendly error message"""
        notifications = data.get("notifications", {})
        error_messages = []

        # Extract all error messages from entity-grouped notifications
        for entity_id, entity_notif in notifications.items():
            if entity_id == "request_warnings":
                continue

            errors = entity_notif.get("errors", [])
            for error in errors:
                msg = error.get("message", "Unknown error")
                field = error.get("field")
                if field:
                    msg = f"{field}: {msg}"
                error_messages.append(msg)

            warnings = entity_notif.get("warnings", [])
            for warning in warnings:
                msg = warning.get("message", "Unknown warning")
                field = warning.get("field")
                if field:
                    msg = f"{field}: {msg}"
                error_messages.append(msg)

        # Format for MCP response
        error_text = "; ".join(error_messages) if error_messages else "Operation failed"
        return {"error": error_text, "status": data.get("status", "error")}

    def _create_list_handler(self, entity: str) -> Callable:
        """Create list handler that calls REST API"""
        async def handler(
            page: int = 1,
            pageSize: int = 50,
            sort_by: str | None = None,
            filter_field: str | None = None,
            filter_value: str | None = None,
            substring_match: str | None = None
        ) -> Dict[str, Any]:
            logger.info(f"list_{entity.lower()} called: page={page}, pageSize={pageSize}")

            # Build query parameters
            params = {"page": page, "pageSize": pageSize}

            if sort_by:
                params["sort"] = sort_by

            if filter_field and filter_value:
                params["filter"] = f"{filter_field}:{filter_value}"

            if substring_match:
                params["substring_match"] = substring_match

            # Make HTTP GET request
            url = f"{self.api_base_url}/{entity.lower()}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                data = response.json()

                # Handle error responses with unified notification format
                if response.status_code >= 400:
                    return self._format_error_response(data)

            items = data.get("data", [])
            pagination = data.get("pagination", {})
            total = pagination.get("total", len(items))

            logger.info(f"list_{entity.lower()} returned {len(items)} items")
            return {
                entity.lower() + "s": items,
                "total": total,
                "page": page,
                "pageSize": pageSize
            }

        return handler

    def _create_get_handler(self, entity: str) -> Callable:
        """Create get handler that calls REST API"""
        async def handler(id: str) -> Dict[str, Any]:
            logger.info(f"get_{entity.lower()} called: id={id}")

            url = f"{self.api_base_url}/{entity.lower()}/{id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                data = response.json()

                # Handle error responses with unified notification format
                if response.status_code >= 400:
                    return self._format_error_response(data)

            item = data.get("data", {})
            if isinstance(item, list) and len(item) > 0:
                item = item[0]

            logger.info(f"get_{entity.lower()} returned item: {id}")
            return item

        return handler

    def _create_create_handler(self, entity: str) -> Callable:
        """Create create handler that calls REST API"""
        async def handler(**kwargs) -> Dict[str, Any]:
            logger.info(f"create_{entity.lower()} called with {len(kwargs)} fields")

            url = f"{self.api_base_url}/{entity.lower()}"
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=kwargs)
                data = response.json()

                # Handle error responses with unified notification format
                if response.status_code >= 400:
                    return self._format_error_response(data)

            item = data.get("data", {})
            if isinstance(item, list) and len(item) > 0:
                item = item[0]

            logger.info(f"create_{entity.lower()} created: {item.get('id')}")
            return item

        return handler

    def _create_update_handler(self, entity: str) -> Callable:
        """Create update handler that calls REST API with PATCH behavior"""
        async def handler(id: str, **kwargs) -> Dict[str, Any]:
            logger.info(f"update_{entity.lower()} called: id={id} with {len(kwargs)} fields")

            # PATCH behavior: fetch existing record, merge, then PUT
            get_url = f"{self.api_base_url}/{entity.lower()}/{id}"
            put_url = f"{self.api_base_url}/{entity.lower()}/{id}"

            async with httpx.AsyncClient() as client:
                # Fetch existing record
                get_response = await client.get(get_url)
                get_data = get_response.json()

                # Handle error responses with unified notification format
                if get_response.status_code >= 400:
                    return self._format_error_response(get_data)

                existing = get_data.get("data", {})
                if isinstance(existing, list) and len(existing) > 0:
                    existing = existing[0]

                # Merge partial update with existing data
                merged = {**existing, **kwargs}
                merged.pop('id', None)  # Remove id from body

                # PUT merged data
                put_response = await client.put(put_url, json=merged)
                put_data = put_response.json()

                # Handle error responses with unified notification format
                if put_response.status_code >= 400:
                    return self._format_error_response(put_data)

            item = put_data.get("data", {})
            if isinstance(item, list) and len(item) > 0:
                item = item[0]

            logger.info(f"update_{entity.lower()} updated: {id}")
            return item

        return handler

    def _create_delete_handler(self, entity: str) -> Callable:
        """Create delete handler that calls REST API"""
        async def handler(id: str) -> Dict[str, Any]:
            logger.info(f"delete_{entity.lower()} called: id={id}")

            url = f"{self.api_base_url}/{entity.lower()}/{id}"
            async with httpx.AsyncClient() as client:
                response = await client.delete(url)
                data = response.json()

                # Handle error responses with unified notification format
                if response.status_code >= 400:
                    return self._format_error_response(data)

            logger.info(f"delete_{entity.lower()} deleted: {id}")
            return {"success": True, "id": id}

        return handler

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools"""
        return self._tools
