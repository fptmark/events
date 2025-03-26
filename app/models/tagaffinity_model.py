

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

class TagAffinity(Document):
    # Base fields
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    profileId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'TagAffinity', 'displayName': 'TagAffinity', 'fields': {'tag': {'type': 'String', 'required': True, 'maxLength': 50, 'displayName': 'Tag'}, 'affinity': {'type': 'Integer', 'required': True, 'min': -100, 'max': 100, 'displayName': 'Affinity'}, 'createdAt': {'type': 'ISODate', 'readOnly': True, 'displayAfterField': '-1', 'required': True, 'autoGenerate': True, 'displayName': 'Created At'}, 'updatedAt': {'type': 'ISODate', 'required': True, 'autoUpdate': True, 'displayAfterField': '-2', 'displayName': 'Updated At'}, 'profileId': {'type': 'ObjectId', 'required': True, 'displayName': 'Profile ID', 'readOnly': True}}}
    
    class Settings:
        name = "tagaffinity"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        # Update timestamp fields for auto-updating fields
        current_time = datetime.now(timezone.utc)
        self.updatedAt = current_time
        return await super().save(*args, **kwargs)


class TagAffinityCreate(BaseModel):
    # Fields for create operations
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    profileId: PydanticObjectId = Field(...)
    @validator('tag')
    def validate_tag(cls, v):
        _custom = {}
        if v is not None and len(v) > 50:
            raise ValueError("tag must be at most 50 characters")
        return v
    @validator('affinity')
    def validate_affinity(cls, v):
        _custom = {}
        if v is not None and v < -100:
            raise ValueError("affinity must be at least -100")
        if v is not None and v > 100:
            raise ValueError("affinity must be at most 100")
        return v
    class Config:
        orm_mode = True


class TagAffinityRead(BaseModel):
    # Fields for read operations
    id: Optional[PydanticObjectId] = Field(alias="_id")
    tag: str = Field(None, max_length=50)
    affinity: int = Field(None, ge=-100, le=100)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    profileId: PydanticObjectId = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}


