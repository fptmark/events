

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

class Profile(Document):
    # Base fields
    name: str = Field(..., max_length=100)
    preferences: dict = Field(None)
    radiusMiles: int = Field(None, ge=0)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    userId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Profile', 'ui': {'title': 'Profile', 'buttonLabel': 'Manage User Profiles', 'description': 'Manage User Preferences'}, 'operations': '', 'fields': {'name': {'type': 'String', 'required': True, 'maxLength': 100}, 'preferences': {'type': 'JSON', 'required': False, 'ui': {'displayPages': 'details'}}, 'radiusMiles': {'type': 'Integer', 'required': False, 'min': 0}, 'createdAt': {'type': 'ISODate', 'required': True, 'autoGenerate': True, 'ui': {'readOnly': True, 'displayAfterField': '-1'}}, 'updatedAt': {'type': 'ISODate', 'required': True, 'autoUpdate': True, 'ui': {'readOnly': True, 'displayAfterField': '-2'}}, 'userId': {'type': 'ObjectId', 'required': True, 'displayName': 'userId', 'readOnly': True, 'ui': {'link': 'entity/User/${value}'}}}}
    
    class Settings:
        name = "profile"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        # Update timestamp fields for auto-updating fields
        current_time = datetime.now(timezone.utc)
        self.updatedAt = current_time
        return await super().save(*args, **kwargs)


class ProfileCreate(BaseModel):
    # Fields for create operations
    name: str = Field(..., max_length=100)
    preferences: dict = Field(None)
    radiusMiles: int = Field(None, ge=0)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    userId: PydanticObjectId = Field(...)
    @validator('name')
    def validate_name(cls, v):
        _custom = {}
        if v is not None and len(v) > 100:
            raise ValueError("name must be at most 100 characters")
        return v
    @validator('radiusMiles')
    def validate_radiusMiles(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError("radiusMiles must be at least 0")
        return v
    class Config:
        orm_mode = True


class ProfileRead(BaseModel):
    # Fields for read operations
    id: PydanticObjectId = Field(alias="_id")
    name: Optional[str] = Field(None, max_length=100)
    preferences: Optional[dict] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    createdAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    userId: Optional[PydanticObjectId] = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}


