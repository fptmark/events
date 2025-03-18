
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

class UserEvent(BaseEntity):
    # UserEvent-specific fields
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'UserEvent', 'displayName': 'UserEvent', 'fields': {'attended': {'type': 'Boolean', 'displayName': 'Attended', 'display': 'always', 'displayAfterField': '', 'widget': 'checkbox', 'required': False}, 'rating': {'type': 'Integer', 'displayName': 'Rating', 'display': 'always', 'displayAfterField': 'attended', 'widget': 'number', 'required': False, 'min': 1, 'max': 5}, 'note': {'type': 'String', 'displayName': 'Note', 'display': 'always', 'displayAfterField': 'rating', 'widget': 'textarea', 'required': False, 'maxLength': 500}, 'userId': {'type': 'ObjectId', 'displayName': 'User ID', 'display': 'always', 'displayAfterField': 'note', 'widget': 'reference', 'required': True}, 'eventId': {'type': 'ObjectId', 'displayName': 'Event ID', 'display': 'always', 'displayAfterField': 'userId', 'widget': 'reference', 'required': True}}}
    
    class Settings:
        name = "userevent"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class UserEventCreate(BaseEntityCreate):
    # UserEvent-specific fields
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
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


class UserEventRead(BaseEntityRead):
    # UserEvent-specific fields
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(None)
    eventId: PydanticObjectId = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}

