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

class Url(Document):
    url: str = Field(..., regex=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Url',
    'fields': {   'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'params': {'required': False, 'type': 'JSON'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'url': {   'pattern': {   'message': 'Bad URL format',
                                            'regex': 'main.url'},
                             'required': True,
                             'type': 'String'}},
    'operations': '',
    'ui': {   'buttonLabel': 'Manage Urls',
              'description': 'Manage Event Urls',
              'title': 'Url'}}

    class Settings:
        name = "url"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class UrlCreate(BaseModel):
    url: str = Field(..., regex=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @validator('url')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     
    class Config:
        orm_mode = True
        extra = Extra.ignore

class UrlUpdate(BaseModel):
    url: str = Field(..., regex=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @validator('url')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     
    class Config:
        orm_mode = True
        extra = Extra.ignore

class UrlRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    url: str = Field(..., regex=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}
