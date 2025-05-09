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

class Profile(Document):
    name: str = Field(..., max_length=100)
    preferences: Optional[str] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Profile',
    'fields': {   'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'name': {   'max_length': 100,
                              'required': True,
                              'type': 'String'},
                  'preferences': {   'required': False,
                                     'type': 'String',
                                     'ui': {'displayPages': 'details'}},
                  'radiusMiles': {   'ge': 0,
                                     'required': False,
                                     'type': 'Integer'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'userId': {   'required': True,
                                'selector': {'fields': ['email', 'username']},
                                'type': 'ObjectId'}},
    'operations': '',
    'ui': {   'buttonLabel': 'Manage User Profiles',
              'description': 'Manage User Preferences',
              'title': 'Profile'}}

    class Settings:
        name = "profile"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        return await cls.find().to_list()

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class ProfileCreate(BaseModel):
    name: str = Field(..., max_length=100)
    preferences: Optional[str] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)

    @field_validator('name', mode='before')
    def validate_name(cls, v):
        _custom = {}
        if v is not None and len(v) > 100:
            raise ValueError('name must be at most 100 characters')
        return v
     
    @field_validator('radiusMiles', mode='before')
    def validate_radiusMiles(cls, v):
        _custom = {}
        if v is not None and int(v) < 0:
            raise ValueError('radiusMiles must be at least 0')
        return v
     
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class ProfileUpdate(BaseModel):
    name: str = Field(..., max_length=100)
    preferences: Optional[str] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)

    @field_validator('name', mode='before')
    def validate_name(cls, v):
        _custom = {}
        if v is not None and len(v) > 100:
            raise ValueError('name must be at most 100 characters')
        return v
     
    @field_validator('radiusMiles', mode='before')
    def validate_radiusMiles(cls, v):
        _custom = {}
        if v is not None and int(v) < 0:
            raise ValueError('radiusMiles must be at least 0')
        return v
     
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class ProfileRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    name: str = Field(..., max_length=100)
    preferences: Optional[str] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={PydanticObjectId: str},
    )
