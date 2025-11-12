"""
RBAC (Role-Based Access Control) service for permission management.

Handles permission extraction from sessions and permission checking for CRUD operations.
"""

from typing import Dict, Optional, Any
from app.core.notify import Notification, HTTP
from app.core.metadata import MetadataService
from app.services.framework import decorators
from app.core.hook import HookService

from app.db.factory import DatabaseFactory
import json5

@decorators.service_config(
    entity=True,
    inputs={"Id": str},
    outputs=["permissions"]
)
class Rbac:
    """RBAC service - utility class for permission management"""

    _entity_configs: Dict[str, Dict[str, Any]] = {}
    _permissions_cache: Dict[str, Dict[str, Any]] = {}  # Cache expanded permissions by roleId

    @classmethod
    async def initialize(cls, entity_configs: dict, runtime_config: dict):
        """
        Initialize RBAC service with multiple entity configurations.

        Args:
            entity_configs: Dict of entity configs, e.g.:
                {'Role': {inputs: {...}, outputs: [...]}}
            runtime_config: Runtime settings (if any)
        """
        cls._permissions_cache = {}
        rbac_entity = next(iter(entity_configs))
        cls.entity_configs = entity_configs

        HookService.register(rbac_entity, False, ['delete'], Rbac.remove_role)   # clear the rbac cache on changes to the rbac entity
        HookService.register(rbac_entity, False, ['update'], Rbac.update_role)   # clear the rbac cache on changes to the rbac entity

        print(f"  RBAC service configured on entity {rbac_entity}")
        return cls

    @classmethod
    def remove_role(cls, doc: Any, count: int, **context):
        """Remove role from cache when deleted"""
        role_id = doc.get('id')
        if role_id and role_id in cls._permissions_cache:
            del cls._permissions_cache[role_id]
            print(f"  RBAC: Removed role {role_id} from cache")
        return doc, count

    @classmethod
    def update_role(cls, doc: Any, count: int, **context):
        """Re-compute and cache permissions when role is updated"""
        role_id = doc.get('id')
        raw_permissions = doc.get('permissions', {})

        if role_id and raw_permissions:
            expanded = cls.compute_permissions(raw_permissions)
            cls._permissions_cache[role_id] = expanded
            print(f"  RBAC: Updated cache for role {role_id}")

        return doc, count

    @classmethod 
    def clear_cache(cls):
        cls._permissions_cache = {}

    @staticmethod
    def compute_permissions(raw_permissions: Dict[str, str]) -> Dict[str, Any]:
        """
        Compute expanded permissions from raw permissions dict.

        Args:
            raw_permissions: Raw permissions like {"*": "cruds", "User": "r"}

        Returns:
            Expanded permissions: {"entity": {"User": "cru", ...}, "reports": []}
        """
        if not raw_permissions:
            return {"entity": {}, "reports": []}

        # Get all entity types from metadata
        all_entities = MetadataService.list_entities()

        # Build entity permissions (specific overrides wildcard)
        entity_perms = {}

        for entity in all_entities:
            # Check for specific entity permission (case-insensitive)
            perm = None
            for key, value in raw_permissions.items():
                if key.lower() == entity.lower():
                    perm = value
                    break

            # If no specific permission, use wildcard
            if perm is None:
                perm = raw_permissions.get("*", "")

            # Only include entities with non-empty permissions
            if perm and perm != "":
                entity_perms[entity] = perm

        return {
            "entity": entity_perms,
            "reports": []  # TODO: Populate based on role/permissions
        }

    @classmethod
    async def _fetch_permissions_from_db(cls, roleId: str, rbac_entity: str) -> Optional[Dict[str, str]]:
        """
        Load raw permissions from database by roleId.

        Args:
            roleId: Role ID to query

        Returns:
            Raw permissions dict like {"*": "cruds"} or None
        """
        # Determine which entity config to use
        config = cls.entity_configs[rbac_entity]
        input_mappings = config.get('inputs', {})
        output_fields = config.get('outputs', [])

        if not input_mappings or not output_fields:
            print(f"ERROR: Rbac config missing fields for {rbac_entity}: inputs={input_mappings}, outputs={output_fields}")
            return None

        # Get field names from mappings
        input_field = list(input_mappings.keys())[0]
        output_field = output_fields[0]

        db = DatabaseFactory.get_instance()
        role_doc = await db.documents.bypass(rbac_entity, {input_field: roleId}, [output_field])

        if role_doc and role_doc.get(output_field):
            return json5.loads(role_doc[output_field])
        return None

    @classmethod
    async def get_permissions(cls, roleId: str, rbac_entity: str = '') -> Optional[Dict[str, Any]]:
        """
        Get expanded permissions for roleId.
        Used by login to return full permissions to client.

        Args:
            roleId: Role ID
            entity: Which entity config to use (defaults to first available)

        Returns:
            Expanded permissions: {"entity": {...}, "reports": [...]}
        """
        # Check cache first (synchronous, fast path)
        if roleId in cls._permissions_cache:
            permissions = cls._permissions_cache[roleId]
        else:
            # Cache miss - load from DB and compute
            raw_permissions = await cls._fetch_permissions_from_db(roleId, rbac_entity)
            permissions = cls.compute_permissions(raw_permissions or {})
            cls._permissions_cache[roleId] = permissions

        return permissions or {}

    @classmethod
    def permitted(cls, roleId: str, entity: str, operation: str) -> bool:
        """
        Check if role has permission for entity operation.

        Args:
            roleId: Role ID from session
            entity: Entity name to check permission for
            operation: Single char operation ('c', 'r', 'u', 'd', 's')

        Returns:
            True if permission granted, False otherwise
        """
        # Check cache first (synchronous, fast path)
        if roleId in cls._permissions_cache:
            permissions = cls._permissions_cache[roleId]
        else:
        #     # Cache miss - load from DB and compute
        #     raw_permissions = await cls._fetch_permissions_from_db(roleId)
        #     permissions = cls.compute_permissions(raw_permissions or {})
        #     cls._permissions_cache[roleId] = permissions
            print(f"Permission cache miss for {roleId}.  This should not happen")

        if not permissions:
            return False

        # Extract entity permissions map from expanded structure
        entity_perms = permissions.get("entity", {})
        if not entity_perms:
            return False

        # Check for entity permission (case-insensitive)
        for perm_entity, perm_ops in entity_perms.items():
            if perm_entity.lower() == entity.lower():
                return operation[0] in perm_ops or "s" in perm_ops  # "s" is for system - all priv

        return False