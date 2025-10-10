from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.services.metadata import MetadataService


class TagAffinityCreate(BaseModel):
    id: str | None = Field(default=None)
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )

class TagAffinityUpdate(BaseModel):
    id: str | None = Field(default=None)
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class TagAffinity(BaseModel):
    id: str | None = Field(default=None)
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'tag': {'type': 'String', 'required': True, 'max_length': 50},
                  'affinity': {   'type': 'Integer',
                                  'required': True,
                                  'ge': -100,
                                  'le': 100},
                  'createdAt': {   'type': 'Date',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'Datetime',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}},
                  'profileId': {'type': 'ObjectId', 'required': True}},
    'operations': '',
    'ui': {'title': 'Tag Affinity', 'buttonLabel': 'Manage Event Affinity'},
    'services': [],
    'uniques': [['profileId', 'tag']]}

    class Settings:
        name = "tagaffinity"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("TagAffinity")

    @classmethod
    async def get_all(cls,
                      sort: List[Tuple[str, str]], 
                      filter: Optional[Dict[str, Any]], 
                      page: int, 
                      pageSize: int, 
                      view_spec: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        "Get paginated, sorted, and filtered list of entity." 
        
        return await DatabaseFactory.get_all("TagAffinity", sort, filter, page, pageSize, view_spec)
        
    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.get("TagAffinity", id, view_spec)

    @classmethod
    async def create(cls, data: TagAffinityCreate, validate: bool = True) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.create("TagAffinity", data.model_dump())

    @classmethod
    async def update(cls, data: TagAffinityUpdate) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.update("TagAffinity", data.model_dump())

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.delete("TagAffinity", id)
