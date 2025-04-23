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

class TagAffinity(Document):
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'TagAffinity',
    'fields': {   'affinity': {   'ge': -100,
                                  'le': 100,
                                  'required': True,
                                  'type': 'Integer'},
                  'createdAt': {   'autoGenerate': True,
                                   'required': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'profileId': {   'displayName': 'profileId',
                                   'readOnly': True,
                                   'required': True,
                                   'type': 'ObjectId'},
                  'tag': {'max_length': 50, 'required': True, 'type': 'String'},
                  'updatedAt': {   'autoUpdate': True,
                                   'required': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-2',
                                             'readOnly': True}}},
    'operations': '',
    'ui': {'buttonLabel': 'Manage Event Affinity', 'title': 'Tag Affinity'}}

    class Settings:
        name = "tagaffinity"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class TagAffinityCreate(BaseModel):
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: PydanticObjectId = Field(...)

    @validator('tag')
    def validate_tag(cls, v):
        _custom = {}
        if v is not None and len(v) > 50:
            raise ValueError('tag must be at most 50 characters')
        return v
     
    @validator('affinity')
    def validate_affinity(cls, v):
        _custom = {}
        if v is not None and v < -100:
            raise ValueError('affinity must be at least -100')
        if v is not None and v > 100:
            raise ValueError('affinity must be at most 100')
        return v
     
    class Config:
        orm_mode = True
        extra = Extra.ignore

class TagAffinityUpdate(BaseModel):
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: PydanticObjectId = Field(...)

    @validator('tag')
    def validate_tag(cls, v):
        _custom = {}
        if v is not None and len(v) > 50:
            raise ValueError('tag must be at most 50 characters')
        return v
     
    @validator('affinity')
    def validate_affinity(cls, v):
        _custom = {}
        if v is not None and v < -100:
            raise ValueError('affinity must be at least -100')
        if v is not None and v > 100:
            raise ValueError('affinity must be at most 100')
        return v
     
    class Config:
        orm_mode = True
        extra = Extra.ignore

class TagAffinityRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}
