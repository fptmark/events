from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.services.metadata import MetadataService

class RecurrenceEnum(str, Enum):
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
 

class EventCreate(BaseModel):
    id: str | None = Field(default=None)
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: str | None = Field(default=None, max_length=200)
    cost: float | None = Field(default=None, ge=0)
    numOfExpectedAttendees: int | None = Field(default=None, ge=0)
    recurrence: RecurrenceEnum | None = Field(default=None)
    tags: List[str] | None = Field(default=None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )

class EventUpdate(BaseModel):
    id: str | None = Field(default=None)
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: str | None = Field(default=None, max_length=200)
    cost: float | None = Field(default=None, ge=0)
    numOfExpectedAttendees: int | None = Field(default=None, ge=0)
    recurrence: RecurrenceEnum | None = Field(default=None)
    tags: List[str] | None = Field(default=None)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class Event(BaseModel):
    id: str | None = Field(default=None)
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: str | None = Field(default=None, max_length=200)
    cost: float | None = Field(default=None, ge=0)
    numOfExpectedAttendees: int | None = Field(default=None, ge=0)
    recurrence: RecurrenceEnum | None = Field(default=None)
    tags: List[str] | None = Field(default=None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'url': {   'type': 'String',
                             'required': True,
                             'pattern': {   'regex': '^https?://[^s]+$',
                                            'message': 'Bad URL format'}},
                  'title': {   'type': 'String',
                               'required': True,
                               'max_length': 200},
                  'dateTime': {'type': 'Date', 'required': True},
                  'location': {   'type': 'String',
                                  'required': False,
                                  'max_length': 200},
                  'cost': {   'type': 'Number',
                              'required': False,
                              'ge': 0,
                              'ui': {'displayPages': 'details'}},
                  'numOfExpectedAttendees': {   'type': 'Integer',
                                                'required': False,
                                                'ge': 0,
                                                'ui': {   'displayPages': 'details'}},
                  'recurrence': {   'type': 'String',
                                    'required': False,
                                    'enum': {   'values': [   'daily',
                                                              'weekly',
                                                              'monthly',
                                                              'yearly']},
                                    'ui': {'displayPages': 'details'}},
                  'tags': {   'type': 'Array[String]',
                              'required': False,
                              'ui': {'displayPages': 'details'}},
                  'createdAt': {   'type': 'Date',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'Datetime',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}}},
    'operations': '',
    'ui': {'title': 'Events', 'buttonLabel': 'Manage Events'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "event"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Event")

    @classmethod
    async def get_all(cls,
                      sort: List[Tuple[str, str]], 
                      filter: Optional[Dict[str, Any]], 
                      page: int, 
                      pageSize: int, 
                      view_spec: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        "Get paginated, sorted, and filtered list of entity." 
        
        db = DatabaseFactory.get_instance()
        return await db.documents.get_all("Event", sort, filter, page, pageSize, view_spec)
        
    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.get("Event", id, view_spec)

    @classmethod
    async def create(cls, data: EventCreate, validate: bool = True) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.create("Event", data.model_dump())

    @classmethod
    async def update(cls, id, data: EventUpdate) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.update("Event", id, data.model_dump())

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.delete("Event", id)
