from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.services.metadata import MetadataService


class UserEventCreate(BaseModel):
    id: str | None = Field(default=None)
    attended: bool | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )

class UserEventUpdate(BaseModel):
    id: str | None = Field(default=None)
    attended: bool | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class UserEvent(BaseModel):
    id: str | None = Field(default=None)
    attended: bool | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'attended': {'type': 'Boolean', 'required': False},
                  'rating': {   'type': 'Integer',
                                'required': False,
                                'ge': 1,
                                'le': 5},
                  'note': {   'type': 'String',
                              'required': False,
                              'max_length': 500,
                              'ui': {'displayPages': 'details'}},
                  'userId': {'type': 'ObjectId', 'required': True},
                  'eventId': {'type': 'ObjectId', 'required': True},
                  'createdAt': {   'type': 'Date',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True},
                                   'autoGenerate': True},
                  'updatedAt': {   'type': 'Datetime',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True,
                                             'clientEdit': True},
                                   'autoUpdate': True}},
    'operations': '',
    'ui': {'title': 'User Events', 'buttonLabel': 'Manage Event Attendance'},
    'services': {},
    'uniques': {}}

    class Settings:
        name = "userevent"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("UserEvent")

    @classmethod
    async def get_all(cls,
                      sort: List[Tuple[str, str]], 
                      filter: Optional[Dict[str, Any]], 
                      page: int, 
                      pageSize: int, 
                      view_spec: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        "Get paginated, sorted, and filtered list of entity." 
        
        db = DatabaseFactory.get_instance()
        return await db.documents.get_all("UserEvent", sort, filter, page, pageSize, view_spec)
        
    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any], top_level: bool = True) -> Tuple[Dict[str, Any], int, Optional[BaseException]]:
        db = DatabaseFactory.get_instance()
        return await db.documents.get("UserEvent", id, view_spec, top_level)

    @classmethod
    async def create(cls, data: UserEventCreate, validate: bool = True) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.create("UserEvent", data.model_dump())

    @classmethod
    async def update(cls, id, data: UserEventUpdate) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.update("UserEvent", id, data.model_dump())

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.delete("UserEvent", id)
