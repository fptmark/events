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

class UserEvent(Document):
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    _metadata: ClassVar[Dict[str, Any]] = {   'entity': 'UserEvent',
    'fields': {   'attended': {'type': 'Boolean', 'required': False},
                  'rating': {   'type': 'Integer',
                                'required': False,
                                'ge': 1,
                                'le': 5},
                  'note': {   'type': 'String',
                              'required': False,
                              'max_length': 500,
                              'ui': {'displayPages': 'details'}},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}},
                  'userId': {'type': 'ObjectId', 'required': True},
                  'eventId': {'type': 'ObjectId', 'required': True}},
    'operations': '',
    'ui': {'title': 'User Events', 'buttonLabel': 'Manage Event Attendance'}}

    class Settings:
        name = "userevent"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        return await cls.find().to_list()

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class UserEventCreate(BaseModel):
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)

    @field_validator('rating', mode='before')
    def validate_rating(cls, v):
        if v is not None and int(v) < 1:
            raise ValueError('rating must be at least 1')
        if v is not None and int(v) > 5:
            raise ValueError('rating must be at most 5')
        return v
     
    @field_validator('note', mode='before')
    def validate_note(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('note must be at most 500 characters')
        return v
     
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class UserEventUpdate(BaseModel):
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)

    @field_validator('rating', mode='before')
    def validate_rating(cls, v):
        if v is not None and int(v) < 1:
            raise ValueError('rating must be at least 1')
        if v is not None and int(v) > 5:
            raise ValueError('rating must be at most 5')
        return v
     
    @field_validator('note', mode='before')
    def validate_note(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('note must be at most 500 characters')
        return v
     
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class UserEventRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={PydanticObjectId: str},
    )
