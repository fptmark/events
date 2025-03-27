

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

class Event(Document):
    # Base fields
    url: str = Field(...)
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Event', 'labels': {'title': 'Events', 'buttonLabel': 'Manage Events'}, 'operations': '', 'fields': {'url': {'type': 'String', 'required': True, 'pattern': '^https?://[^s]+$', 'pattern.message': 'Bad URL format', 'displayName': 'Url'}, 'title': {'type': 'String', 'required': True, 'maxLength': 200, 'displayName': 'Title'}, 'dateTime': {'type': 'ISODate', 'required': True, 'displayName': 'Date Time'}, 'location': {'type': 'String', 'required': False, 'maxLength': 200, 'displayName': 'Location'}, 'cost': {'type': 'Number', 'displayPages': 'details', 'required': False, 'min': 0, 'displayName': 'Cost'}, 'numOfExpectedAttendees': {'type': 'Integer', 'displayPages': 'details', 'required': False, 'min': 0, 'displayName': 'Num Of Expected Attendees'}, 'recurrence': {'type': 'String', 'displayPages': 'details', 'required': False, 'options': ['daily', 'weekly', 'monthly', 'yearly'], 'displayName': 'Recurrence'}, 'tags': {'type': 'Array[String]', 'displayPages': 'details', 'required': False, 'displayName': 'Tags'}, 'createdAt': {'type': 'ISODate', 'readOnly': True, 'displayAfterField': '-1', 'required': True, 'autoGenerate': True, 'displayName': 'Created At'}, 'updatedAt': {'type': 'ISODate', 'required': True, 'autoUpdate': True, 'displayAfterField': '-2', 'displayName': 'Updated At'}}}
    
    class Settings:
        name = "event"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        # Update timestamp fields for auto-updating fields
        current_time = datetime.now(timezone.utc)
        self.updatedAt = current_time
        return await super().save(*args, **kwargs)


class EventCreate(BaseModel):
    # Fields for create operations
    url: str = Field(...)
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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


class EventRead(BaseModel):
    # Fields for read operations
    id: Optional[PydanticObjectId] = Field(alias="_id")
    url: str = Field(None)
    title: str = Field(None, max_length=200)
    dateTime: datetime = Field(None)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}


