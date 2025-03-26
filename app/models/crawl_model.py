

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

class Crawl(Document):
    # Base fields
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    urlId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Crawl', 'displayName': 'Crawl', 'fields': {'lastParsedDate': {'type': 'ISODate', 'required': False, 'displayName': 'Last Parsed Date'}, 'parseStatus': {'type': 'JSON', 'required': False, 'displayName': 'Parse Status'}, 'errorsEncountered': {'type': 'Array[String]', 'required': False, 'displayName': 'Errors Encountered'}, 'createdAt': {'type': 'ISODate', 'readOnly': True, 'displayAfterField': '-1', 'required': True, 'autoGenerate': True, 'displayName': 'Created At'}, 'updatedAt': {'type': 'ISODate', 'required': True, 'autoUpdate': True, 'displayAfterField': '-2', 'displayName': 'Updated At'}, 'urlId': {'type': 'ObjectId', 'required': True, 'displayName': 'Url ID', 'readOnly': True}}}
    
    class Settings:
        name = "crawl"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        # Update timestamp fields for auto-updating fields
        current_time = datetime.now(timezone.utc)
        self.updatedAt = current_time
        return await super().save(*args, **kwargs)


class CrawlCreate(BaseModel):
    # Fields for create operations
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    urlId: PydanticObjectId = Field(...)
    class Config:
        orm_mode = True


class CrawlRead(BaseModel):
    # Fields for read operations
    id: Optional[PydanticObjectId] = Field(alias="_id")
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    urlId: PydanticObjectId = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}


