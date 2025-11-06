from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.core.metadata import MetadataService


class AuthCreate(BaseModel):
    id: str | None = Field(default=None)
    name: str = Field(..., min_length=4)
    password: str = Field(..., min_length=8)
    roleId: str = Field(...)
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )

class AuthUpdate(BaseModel):
    id: str | None = Field(default=None)
    name: str = Field(..., min_length=4)
    password: str = Field(..., min_length=8)
    roleId: str = Field(...)
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class Auth(BaseModel):
    id: str | None = Field(default=None)
    name: str = Field(..., min_length=4)
    password: str = Field(..., min_length=8)
    roleId: str = Field(...)

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'name': {'type': 'String', 'required': True, 'min_length': 4},
                  'password': {   'type': 'String',
                                  'required': True,
                                  'min_length': 8,
                                  'encrypt': True},
                  'roleId': {   'type': 'ObjectId',
                                'required': True,
                                'ui': {   'displayName': 'Role',
                                          'show': {   'displayInfo': [   {   'fields': [   'role',
                                                                                           'permissions']}]}}}},
    'ui': {},
    'services': {   'authn.cookies.redis': {   'inputs': {   'login': 'name',
                                                             'password': 'password'},
                                               'outputs': ['roleId'],
                                               'entity': 'Auth'}},
    'uniques': [['name']]}

    class Settings:
        name = "auth"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Auth")

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
        return await db.documents.get_all("Auth", sort, filter, page, pageSize, view_spec, filter_matching)
        
    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any], top_level: bool = True) -> Tuple[Dict[str, Any], int, Optional[BaseException]]:
        db = DatabaseFactory.get_instance()
        return await db.documents.get("Auth", id, view_spec, top_level)

    @classmethod
    async def create(cls, data: AuthCreate, validate: bool = True) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.create("Auth", data.model_dump())

    @classmethod
    async def update(cls, id, data: AuthUpdate) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.update("Auth", id, data.model_dump())

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.delete("Auth", id)
