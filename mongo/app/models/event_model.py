from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, ClassVar, Self
from collections.abc import Sequence
from datetime import datetime, timezone
import re
import app.utils as helpers

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"

class Event(Document):
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Event',
    'fields': {   'cost': {   'ge': 0,
                              'required': False,
                              'type': 'Number',
                              'ui': {'displayPages': 'details'}},
                  'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'dateTime': {'required': True, 'type': 'ISODate'},
                  'location': {   'max_length': 200,
                                  'required': False,
                                  'type': 'String'},
                  'numOfExpectedAttendees': {   'ge': 0,
                                                'required': False,
                                                'type': 'Integer',
                                                'ui': {   'displayPages': 'details'}},
                  'recurrence': {   'enum': {   'values': [   'daily',
                                                              'weekly',
                                                              'monthly',
                                                              'yearly']},
                                    'required': False,
                                    'type': 'String',
                                    'ui': {'displayPages': 'details'}},
                  'tags': {   'required': False,
                              'type': 'Array[String]',
                              'ui': {'displayPages': 'details'}},
                  'title': {   'max_length': 200,
                               'required': True,
                               'type': 'String'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'url': {   'pattern': {   'message': 'Bad URL format',
                                            'regex': '^https?://[^s]+$'},
                             'required': True,
                             'type': 'String'}},
    'operations': '',
    'ui': {'buttonLabel': 'Manage Events', 'title': 'Events'}}

    class Settings:
        name = "event"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        return await cls.find().to_list()

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class EventCreate(BaseModel):
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'^https?://[^s]+$', v):
            raise ValueError('Bad URL format')
        return v
     
    @field_validator('title', mode='before')
    def validate_title(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('title must be at most 200 characters')
        return v
     
    @field_validator('dateTime', mode='before')
    def parse_dateTime(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    @field_validator('location', mode='before')
    def validate_location(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('location must be at most 200 characters')
        return v
     
    @field_validator('cost', mode='before')
    def validate_cost(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('cost must be at least 0')
        return v
     
    @field_validator('numOfExpectedAttendees', mode='before')
    def validate_numOfExpectedAttendees(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('numOfExpectedAttendees must be at least 0')
        return v
     
    @field_validator('recurrence', mode='before')
    def validate_recurrence(cls, v):
        _custom = {}
        allowed = ['daily', 'weekly', 'monthly', 'yearly']
        if v is not None and v not in allowed:
            raise ValueError('recurrence must be one of ' + ','.join(allowed))
        return v
     
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class EventUpdate(BaseModel):
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'^https?://[^s]+$', v):
            raise ValueError('Bad URL format')
        return v
     
    @field_validator('title', mode='before')
    def validate_title(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('title must be at most 200 characters')
        return v
     
    @field_validator('dateTime', mode='before')
    def parse_dateTime(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    @field_validator('location', mode='before')
    def validate_location(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('location must be at most 200 characters')
        return v
     
    @field_validator('cost', mode='before')
    def validate_cost(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('cost must be at least 0')
        return v
     
    @field_validator('numOfExpectedAttendees', mode='before')
    def validate_numOfExpectedAttendees(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('numOfExpectedAttendees must be at least 0')
        return v
     
    @field_validator('recurrence', mode='before')
    def validate_recurrence(cls, v):
        _custom = {}
        allowed = ['daily', 'weekly', 'monthly', 'yearly']
        if v is not None and v not in allowed:
            raise ValueError('recurrence must be one of ' + ','.join(allowed))
        return v
     
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class EventRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={PydanticObjectId: str},
    )
