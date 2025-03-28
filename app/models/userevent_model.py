

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

class UserEvent(Document):
    # Base fields
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'UserEvent', 'ui': {'title': 'User Events', 'buttonLabel': 'Manage Event Attendance'}, 'operations': '', 'fields': {'attended': {'type': 'Boolean', 'required': False}, 'rating': {'type': 'Integer', 'required': False, 'min': 1, 'max': 5}, 'note': {'type': 'String', 'required': False, 'maxLength': 500, 'ui': {'displayPages': 'details'}}, 'createdAt': {'type': 'ISODate', 'required': True, 'autoGenerate': True, 'ui': {'readOnly': True, 'displayAfterField': '-1'}}, 'updatedAt': {'type': 'ISODate', 'required': True, 'autoUpdate': True, 'ui': {'displayAfterField': '-2'}}, 'userId': {'type': 'ObjectId', 'required': True, 'displayName': 'User ID', 'readOnly': True}, 'eventId': {'type': 'ObjectId', 'required': True, 'displayName': 'Event ID', 'readOnly': True}}}
    
    class Settings:
        name = "userevent"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        # Update timestamp fields for auto-updating fields
        current_time = datetime.now(timezone.utc)
        self.updatedAt = current_time
        return await super().save(*args, **kwargs)


class UserEventCreate(BaseModel):
    # Fields for create operations
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)
    @validator('rating')
    def validate_rating(cls, v):
        _custom = {}
        if v is not None and v < 1:
            raise ValueError("rating must be at least 1")
        if v is not None and v > 5:
            raise ValueError("rating must be at most 5")
        return v
    @validator('note')
    def validate_note(cls, v):
        _custom = {}
        if v is not None and len(v) > 500:
            raise ValueError("note must be at most 500 characters")
        return v
    class Config:
        orm_mode = True


class UserEventRead(BaseModel):
    # Fields for read operations
    id: Optional[PydanticObjectId] = Field(alias="_id")
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    userId: PydanticObjectId = Field(None)
    eventId: PydanticObjectId = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}


