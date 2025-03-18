
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

class Profile(BaseEntity):
    # Profile-specific fields
    name: str = Field(..., max_length=100)
    preferences: Optional[dict] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Profile', 'displayName': 'Profile', 'fields': {'name': {'type': 'String', 'displayName': 'Name', 'display': 'always', 'displayAfterField': '', 'widget': 'text', 'required': True, 'maxLength': 100}, 'preferences': {'type': 'JSON', 'displayName': 'Preferences', 'display': 'always', 'displayAfterField': 'name', 'widget': 'jsoneditor', 'required': False}, 'radiusMiles': {'type': 'Integer', 'displayName': 'Radius Miles', 'display': 'always', 'displayAfterField': 'preferences', 'widget': 'number', 'required': False, 'min': 0}, 'userId': {'type': 'ObjectId', 'displayName': 'User ID', 'display': 'always', 'displayAfterField': 'radiusMiles', 'widget': 'reference', 'required': True}}}
    
    class Settings:
        name = "profile"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class ProfileCreate(BaseEntityCreate):
    # Profile-specific fields
    name: str = Field(..., max_length=100)
    preferences: Optional[dict] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
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


class ProfileRead(BaseEntityRead):
    # Profile-specific fields
    name: str = Field(None, max_length=100)
    preferences: Optional[dict] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}

