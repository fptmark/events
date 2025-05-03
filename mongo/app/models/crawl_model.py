from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, field_validator, ConfigDict
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

class Crawl(Document):
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Crawl',
    'fields': {   'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'errorsEncountered': {   'required': False,
                                           'type': 'Array[String]'},
                  'lastParsedDate': {'required': False, 'type': 'ISODate'},
                  'parseStatus': {'required': False, 'type': 'JSON'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'urlId': {   'displayName': 'urlId',
                               'readOnly': True,
                               'required': True,
                               'type': 'ObjectId'}},
    'operations': 'rd',
    'ui': {   'buttonLabel': 'Manage Crawls',
              'description': 'Manage Crawls of Event sites',
              'title': 'Crawls'}}

    class Settings:
        name = "crawl"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class CrawlCreate(BaseModel):
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)

    @field_validator('lastParsedDate', mode='before')
    def parse_lastParsedDate(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class CrawlUpdate(BaseModel):
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)

    @field_validator('lastParsedDate', mode='before')
    def parse_lastParsedDate(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class CrawlRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={PydanticObjectId: str},
    )
