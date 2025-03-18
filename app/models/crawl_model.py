
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

class Crawl(BaseEntity):
    # Crawl-specific fields
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Crawl', 'displayName': 'Crawl', 'fields': {'lastParsedDate': {'type': 'ISODate', 'displayName': 'Last Parsed Date', 'display': 'always', 'displayAfterField': '', 'widget': 'date', 'required': False}, 'parseStatus': {'type': 'JSON', 'displayName': 'Parse Status', 'display': 'always', 'displayAfterField': 'lastParsedDate', 'widget': 'jsoneditor', 'required': False}, 'errorsEncountered': {'type': 'Array[String]', 'displayName': 'Errors Encountered', 'display': 'always', 'displayAfterField': 'parseStatus', 'widget': 'multiselect', 'required': False}, 'urlId': {'type': 'ObjectId', 'displayName': 'Url ID', 'display': 'always', 'displayAfterField': 'errorsEncountered', 'widget': 'reference', 'required': True}}}
    
    class Settings:
        name = "crawl"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class CrawlCreate(BaseEntityCreate):
    # Crawl-specific fields
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)
    class Config:
        orm_mode = True


class CrawlRead(BaseEntityRead):
    # Crawl-specific fields
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}

