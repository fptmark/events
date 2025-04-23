from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Extra, Field, validator
from typing import Optional, List, Dict, Any, ClassVar
from datetime import datetime, timezone
import re
import app.utilities.utils as helpers

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"

class Event(Document):
    url: str = Field(..., regex=r"^https?://[^s]+$")
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
                                   'required': True,
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
                                   'required': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-2',
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

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class EventCreate(BaseModel):
    url: str = Field(..., regex=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    @validator('url')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'^https?://[^s]+$', v):
            raise ValueError('Bad URL format')
        return v
     
    @validator('title')
    def validate_title(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('title must be at most 200 characters')
        return v
     
    @validator('dateTime', pre=True)
    def parse_dateTime(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    @validator('location')
    def validate_location(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('location must be at most 200 characters')
        return v
     
    @validator('cost')
    def validate_cost(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('cost must be at least 0')
        return v
     
    @validator('numOfExpectedAttendees')
    def validate_numOfExpectedAttendees(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('numOfExpectedAttendees must be at least 0')
        return v
     
    @validator('recurrence')
    def validate_recurrence(cls, v):
        _custom = {}
        allowed = ['daily', 'weekly', 'monthly', 'yearly']
        if v is not None and v not in allowed:
            raise ValueError('recurrence must be one of ' + ','.join(allowed))
        return v
     
    class Config:
        orm_mode = True
        extra = Extra.ignore

class EventUpdate(BaseModel):
    url: str = Field(..., regex=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    @validator('url')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'^https?://[^s]+$', v):
            raise ValueError('Bad URL format')
        return v
     
    @validator('title')
    def validate_title(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('title must be at most 200 characters')
        return v
     
    @validator('dateTime', pre=True)
    def parse_dateTime(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    @validator('location')
    def validate_location(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('location must be at most 200 characters')
        return v
     
    @validator('cost')
    def validate_cost(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('cost must be at least 0')
        return v
     
    @validator('numOfExpectedAttendees')
    def validate_numOfExpectedAttendees(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('numOfExpectedAttendees must be at least 0')
        return v
     
    @validator('recurrence')
    def validate_recurrence(cls, v):
        _custom = {}
        allowed = ['daily', 'weekly', 'monthly', 'yearly']
        if v is not None and v not in allowed:
            raise ValueError('recurrence must be one of ' + ','.join(allowed))
        return v
     
    class Config:
        orm_mode = True
        extra = Extra.ignore

class EventRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    url: str = Field(..., regex=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}
