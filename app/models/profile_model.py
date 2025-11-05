from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.core.metadata import MetadataService


class ProfileCreate(BaseModel):
    id: str | None = Field(default=None)
    name: str = Field(..., max_length=100)
    preferences: str | None = Field(default=None)
    radiusMiles: int | None = Field(default=None, ge=0)
    userId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )

class ProfileUpdate(BaseModel):
    id: str | None = Field(default=None)
    name: str = Field(..., max_length=100)
    preferences: str | None = Field(default=None)
    radiusMiles: int | None = Field(default=None, ge=0)
    userId: str = Field(...)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class Profile(BaseModel):
    id: str | None = Field(default=None)
    name: str = Field(..., max_length=100)
    preferences: str | None = Field(default=None)
    radiusMiles: int | None = Field(default=None, ge=0)
    userId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'name': {   'type': 'String',
                              'required': True,
                              'max_length': 100},
                  'preferences': {   'type': 'String',
                                     'required': False,
                                     'ui': {'displayPages': 'details'}},
                  'radiusMiles': {   'type': 'Integer',
                                     'required': False,
                                     'ge': 0},
                  'userId': {   'type': 'ObjectId',
                                'required': True,
                                'ui': {   'show': {   'displayInfo': [   {   'displayPages': 'summary',
                                                                             'fields': [   'email']},
                                                                         {   'displayPages': 'create|edit',
                                                                             'fields': [   'email',
                                                                                           'username']}]}}},
                  'createdAt': {   'type': 'Date',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True},
                                   'autoGenerate': True},
                  'updatedAt': {   'type': 'Datetime',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True,
                                             'clientEdit': True},
                                   'autoUpdate': True}},
    'ui': {   'title': 'Profile',
              'buttonLabel': 'Manage User Profiles',
              'description': 'Manage User Preferences'},
    'services': {},
    'uniques': [['name', 'userId']]}

    class Settings:
        name = "profile"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Profile")

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
        return await db.documents.get_all("Profile", sort, filter, page, pageSize, view_spec, filter_matching)
        
    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any], top_level: bool = True) -> Tuple[Dict[str, Any], int, Optional[BaseException]]:
        db = DatabaseFactory.get_instance()
        return await db.documents.get("Profile", id, view_spec, top_level)

    @classmethod
    async def create(cls, data: ProfileCreate, validate: bool = True) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.create("Profile", data.model_dump())

    @classmethod
    async def update(cls, id, data: ProfileUpdate) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.update("Profile", id, data.model_dump())

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.delete("Profile", id)
