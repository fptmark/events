
from app.models.baseentity_model import BaseEntity, BaseEntityCreate, BaseEntityRead

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, ClassVar
from datetime import datetime, timezone
import re
import json

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"

class Event(BaseEntity):
    # Event-specific fields
    url: str = Field(...)
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Event', 'displayName': 'Event', 'fields': {'url': {'type': 'String', 'displayName': 'Url', 'display': 'always', 'displayAfterField': '', 'widget': 'text', 'required': True, 'pattern': '^https?://[^s]+$'}, 'title': {'type': 'String', 'displayName': 'Title', 'display': 'always', 'displayAfterField': 'url', 'widget': 'textarea', 'required': True, 'maxLength': 200}, 'dateTime': {'type': 'ISODate', 'displayName': 'Date Time', 'display': 'always', 'displayAfterField': 'title', 'widget': 'date', 'required': True}, 'location': {'type': 'String', 'displayName': 'Location', 'display': 'always', 'displayAfterField': 'dateTime', 'widget': 'textarea', 'required': False, 'maxLength': 200}, 'cost': {'type': 'Number', 'displayName': 'Cost', 'display': 'always', 'displayAfterField': 'location', 'widget': 'number', 'required': False, 'min': 0}, 'numOfExpectedAttendees': {'type': 'Integer', 'displayName': 'Num Of Expected Attendees', 'display': 'always', 'displayAfterField': 'cost', 'widget': 'number', 'required': False, 'min': 0}, 'recurrence': {'type': 'String', 'displayName': 'Recurrence', 'display': 'always', 'displayAfterField': 'numOfExpectedAttendees', 'widget': 'select', 'required': False, 'options': ['daily', 'weekly', 'monthly', 'yearly']}, 'tags': {'type': 'Array[String]', 'displayName': 'Tags', 'display': 'always', 'displayAfterField': 'recurrence', 'widget': 'multiselect', 'required': False}}}
    
    class Settings:
        name = "event"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class EventCreate(BaseEntityCreate):
    # Event-specific fields
    url: str = Field(...)
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)
    @validator('url')
    def validate_url(cls, v):
        _custom = {"pattern": "Bad URL format"}
        if v is not None and not re.match(r'^https?://[^s]+$', v):
            raise ValueError(_custom["pattern"])
        return v
    @validator('title')
    def validate_title(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError("title must be at most 200 characters")
        return v
    @validator('location')
    def validate_location(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError("location must be at most 200 characters")
        return v
    @validator('cost')
    def validate_cost(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError("cost must be at least 0")
        return v
    @validator('numOfExpectedAttendees')
    def validate_numOfExpectedAttendees(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError("numOfExpectedAttendees must be at least 0")
        return v
    @validator('recurrence')
    def validate_recurrence(cls, v):
        _custom = {}
        allowed = ["daily", "weekly", "monthly", "yearly"]
        if v is not None and v not in allowed:
            raise ValueError("recurrence must be one of " + ", ".join(allowed))
        return v
    class Config:
        orm_mode = True


class EventRead(BaseEntityRead):
    # Event-specific fields
    url: str = Field(None)
    title: str = Field(None, max_length=200)
    dateTime: datetime = Field(None)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}

