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

class Url(Document):
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    _metadata: ClassVar[Dict[str, Any]] = {   'entity': 'Url',
    'fields': {   'url': {   'type': 'String',
                             'required': True,
                             'pattern': {   'regex': 'main.url',
                                            'message': 'Bad URL format'}},
                  'params': {'type': 'JSON', 'required': False},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}}},
    'operations': '',
    'ui': {   'title': 'Url',
              'buttonLabel': 'Manage Urls',
              'description': 'Manage Event Urls'}}

    class Settings:
        name = "url"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        return await cls.find().to_list()

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class UrlCreate(BaseModel):
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class UrlUpdate(BaseModel):
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class UrlRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={PydanticObjectId: str},
    )
