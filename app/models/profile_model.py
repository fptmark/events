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

class Profile(Document):
    name: str = Field(..., max_length=100)
    preferences: Optional[Dict[str, Any]] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Profile',
    'fields': {   'createdAt': {   'autoGenerate': True,
                                   'required': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'name': {   'max_length': 100,
                              'required': True,
                              'type': 'String'},
                  'preferences': {   'required': False,
                                     'type': 'JSON',
                                     'ui': {'displayPages': 'details'}},
                  'radiusMiles': {   'ge': 0,
                                     'required': False,
                                     'type': 'Integer'},
                  'updatedAt': {   'autoUpdate': True,
                                   'required': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-2',
                                             'readOnly': True}},
                  'userId': {   'displayName': 'userId',
                                'readOnly': True,
                                'required': True,
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

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class ProfileCreate(BaseModel):
    name: str = Field(..., max_length=100)
    preferences: Optional[Dict[str, Any]] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)

    @validator('name')
    def validate_name(cls, v):
        _custom = {}
        if v is not None and len(v) > 100:
            raise ValueError('name must be at most 100 characters')
        return v
     
    @validator('radiusMiles')
    def validate_radiusMiles(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('radiusMiles must be at least 0')
        return v
     
    class Config:
        orm_mode = True
        extra = Extra.ignore

class ProfileUpdate(BaseModel):
    name: str = Field(..., max_length=100)
    preferences: Optional[Dict[str, Any]] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)

    @validator('name')
    def validate_name(cls, v):
        _custom = {}
        if v is not None and len(v) > 100:
            raise ValueError('name must be at most 100 characters')
        return v
     
    @validator('radiusMiles')
    def validate_radiusMiles(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('radiusMiles must be at least 0')
        return v
     
    class Config:
        orm_mode = True
        extra = Extra.ignore

class ProfileRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    name: str = Field(..., max_length=100)
    preferences: Optional[Dict[str, Any]] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}
