from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.core.metadata import MetadataService


class RoleCreate(BaseModel):
    id: str | None = Field(default=None)
    role: str = Field(...)
    permissions: str = Field(...)
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )

class RoleUpdate(BaseModel):
    id: str | None = Field(default=None)
    role: str = Field(...)
    permissions: str = Field(...)
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class Role(BaseModel):
    id: str | None = Field(default=None)
    role: str = Field(...)
    permissions: str = Field(...)

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'role': {'type': 'String', 'required': True},
                  'permissions': {'type': 'String', 'required': True}},
    'ui': {},
    'services': {   'authz': {   'provider': 'rbac',
                                 'inputs': {'Id': 'roleId'},
                                 'outputs': ['permissions'],
                                 'entity': 'Role'}},
    'uniques': [['role']]}

    class Settings:
        name = "role"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Role")

    @classmethod
    async def get_all(cls,
                      sort: List[Tuple[str, str]], 
                      filter: Optional[Dict[str, Any]], 
                      page: int, 
                      pageSize: int, 
                      view_spec: Dict[str, Any],
                      filter_matching: str = "contains") -> Tuple[List[Dict[str, Any]], int]:
        "Get paginated, sorted, and filtered list of entity." 
        
        db = DatabaseFactory.get_instance()
        return await db.documents.get_all("Role", sort, filter, page, pageSize, view_spec, filter_matching)
        
    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.get("Role", id, view_spec)

    @classmethod
    async def create(cls, data: RoleCreate, validate: bool = True) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.create("Role", data.model_dump())

    @classmethod
    async def update(cls, id, data: RoleUpdate) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.update("Role", id, data.model_dump())

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.delete("Role", id)
