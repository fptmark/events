"""
Generic MCP tool registry.
Auto-generates tools for all entities from schema.yaml.
"""
from typing import Any, Dict, List, Callable
import logging
import sys
from pathlib import Path

from app.db import DatabaseFactory
from app.services.metadata import MetadataService
from app.services.model import ModelService
from .schemas import get_generator

# Add schema2rest to path for Schema class
schema2rest_path = Path(__file__).resolve().parent.parent.parent.parent / "schema2rest" / "src"
if str(schema2rest_path) not in sys.path:
    sys.path.insert(0, str(schema2rest_path))

from common.schema import Schema

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Generic tool registry that auto-generates CRUD tools for all entities.
    """

    def __init__(self, schema_path: str = "schema.yaml"):
        """
        Initialize tool registry.

        Args:
            schema_path: Path to schema.yaml file
        """
        self.schema = Schema(schema_path)
        self.schema_gen = get_generator(schema_path)
        self._tools = []

    def _create_list_handler(self, entity: str) -> Callable:
        """
        Create a list handler function for an entity.

        Args:
            entity: Entity name

        Returns:
            Async handler function
        """
        async def handler(
            page: int = 1,
            pageSize: int = 50,
            sort_by: str | None = None,
            filter_field: str | None = None,
            filter_value: str | None = None
        ) -> Dict[str, Any]:
            logger.info(f"list_{entity.lower()} called: page={page}, pageSize={pageSize}")

            # Build sort parameter
            sort = []
            if sort_by:
                direction = "desc" if sort_by.startswith("-") else "asc"
                field = sort_by.lstrip("-")
                sort = [(field, direction)]
            else:
                sort = [("createdAt", "desc")]

            # Build filter parameter
            filter_dict = {}
            if filter_field and filter_value:
                filter_dict[filter_field] = filter_value

            # Call entity.get_all
            Model = ModelService.get_model_class(entity)
            view_spec = {"fields": "*"}

            try:
                items, total = await Model.get_all(
                    sort=sort,
                    filter=filter_dict if filter_dict else None,
                    page=page,
                    pageSize=pageSize,
                    view_spec=view_spec,
                    filter_matching="exact"
                )

                logger.info(f"list_{entity.lower()} returned {len(items)} items (total: {total})")
                return {
                    entity.lower() + "s": items,
                    "total": total,
                    "page": page,
                    "pageSize": pageSize
                }
            except Exception as e:
                logger.error(f"list_{entity.lower()} error: {e}")
                raise

        return handler

    def _create_get_handler(self, entity: str) -> Callable:
        """
        Create a get handler function for an entity.

        Args:
            entity: Entity name

        Returns:
            Async handler function
        """
        async def handler(id: str) -> Dict[str, Any]:
            logger.info(f"get_{entity.lower()} called: id={id}")

            Model = ModelService.get_model_class(entity)
            view_spec = {"fields": "*"}

            try:
                item, status_code, error = await Model.get(id, view_spec)

                if error:
                    logger.error(f"get_{entity.lower()} error: {error}")
                    raise error

                if status_code != 200:
                    raise ValueError(f"{entity} not found: {id}")

                logger.info(f"get_{entity.lower()} returned item: {id}")
                return item
            except Exception as e:
                logger.error(f"get_{entity.lower()} error: {e}")
                raise

        return handler

    def _create_create_handler(self, entity: str) -> Callable:
        """
        Create a create handler function for an entity.

        Args:
            entity: Entity name

        Returns:
            Async handler function
        """
        async def handler(**kwargs) -> Dict[str, Any]:
            logger.info(f"create_{entity.lower()} called with {len(kwargs)} fields")

            # Get Create model
            CreateModel = ModelService.get_create_class(entity)
            if not CreateModel:
                raise ValueError(f"{entity}Create model not found")

            try:
                # Validate with Pydantic
                create_instance = CreateModel(**kwargs)

                # Create entity
                Model = ModelService.get_model_class(entity)
                created_item, status_code = await Model.create(create_instance)

                if status_code != 201:
                    raise ValueError(f"Failed to create {entity}: status {status_code}")

                logger.info(f"create_{entity.lower()} created: {created_item.get('id')}")
                return created_item
            except Exception as e:
                logger.error(f"create_{entity.lower()} error: {e}")
                raise

        return handler

    def _create_update_handler(self, entity: str) -> Callable:
        """
        Create an update handler function for an entity.

        Args:
            entity: Entity name

        Returns:
            Async handler function
        """
        async def handler(id: str, **kwargs) -> Dict[str, Any]:
            logger.info(f"update_{entity.lower()} called: id={id} with {len(kwargs)} fields")

            # Get Update model
            UpdateModel = ModelService.get_update_class(entity)
            if not UpdateModel:
                raise ValueError(f"{entity}Update model not found")

            try:
                # Validate with Pydantic
                update_instance = UpdateModel(**kwargs)

                # Update entity
                Model = ModelService.get_model_class(entity)
                updated_item, status_code = await Model.update(id, update_instance)

                if status_code != 200:
                    raise ValueError(f"Failed to update {entity}: status {status_code}")

                logger.info(f"update_{entity.lower()} updated: {id}")
                return updated_item
            except Exception as e:
                logger.error(f"update_{entity.lower()} error: {e}")
                raise

        return handler

    def _create_delete_handler(self, entity: str) -> Callable:
        """
        Create a delete handler function for an entity.

        Args:
            entity: Entity name

        Returns:
            Async handler function
        """
        async def handler(id: str) -> Dict[str, Any]:
            logger.info(f"delete_{entity.lower()} called: id={id}")

            Model = ModelService.get_model_class(entity)

            try:
                result, status_code = await Model.delete(id)

                if status_code != 200:
                    raise ValueError(f"Failed to delete {entity}: status {status_code}")

                logger.info(f"delete_{entity.lower()} deleted: {id}")
                return {"success": True, "id": id}
            except Exception as e:
                logger.error(f"delete_{entity.lower()} error: {e}")
                raise

        return handler

    def register_entity(self, entity: str, operations: str = "crud") -> None:
        """
        Register CRUD tools for an entity.

        Args:
            entity: Entity name (e.g., "User")
            operations: Operations to support (e.g., "crud", "r", "cru")
                c = create, r = read (list/get), u = update, d = delete
        """
        logger.info(f"Registering tools for {entity} with operations: {operations}")

        # List tool (read)
        if "r" in operations:
            self._tools.append({
                "name": f"list_{entity.lower()}s",
                "description": f"List {entity.lower()}s with optional filtering, sorting, and pagination",
                "input_schema": self.schema_gen.generate_list_schema(entity),
                "handler": self._create_list_handler(entity)
            })

            # Get tool (read)
            self._tools.append({
                "name": f"get_{entity.lower()}",
                "description": f"Get a single {entity.lower()} by ID",
                "input_schema": self.schema_gen.generate_get_schema(entity),
                "handler": self._create_get_handler(entity)
            })

        # Create tool
        if "c" in operations:
            self._tools.append({
                "name": f"create_{entity.lower()}",
                "description": f"Create a new {entity.lower()}",
                "input_schema": self.schema_gen.generate_create_schema(entity),
                "handler": self._create_create_handler(entity)
            })

        # Update tool
        if "u" in operations:
            self._tools.append({
                "name": f"update_{entity.lower()}",
                "description": f"Update an existing {entity.lower()}",
                "input_schema": self.schema_gen.generate_update_schema(entity),
                "handler": self._create_update_handler(entity)
            })

        # Delete tool
        if "d" in operations:
            self._tools.append({
                "name": f"delete_{entity.lower()}",
                "description": f"Delete a {entity.lower()} by ID",
                "input_schema": self.schema_gen.generate_delete_schema(entity),
                "handler": self._create_delete_handler(entity)
            })

    def register_all_entities(self) -> None:
        """
        Register tools for all entities from schema.yaml.
        Uses 'operations' field from schema to determine which tools to create.
        """
        # Get concrete entities from schema
        entities_dict = self.schema.concrete_entities()
        entities = list(entities_dict.keys())
        logger.info(f"Auto-registering tools for {len(entities)} entities")

        for entity in entities:
            # Get operations from entity definition in schema
            entity_def = entities_dict[entity]
            operations = entity_def.get("operations", "crud")
            self.register_entity(entity, operations)

        logger.info(f"Registered {len(self._tools)} total tools")

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Get all registered tools.

        Returns:
            List of tool definitions
        """
        return self._tools
