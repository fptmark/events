

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

class Url(Document):
    # Base fields
    url: str = Field(..., regex=r"main.url")
    params: dict = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Url', 'ui': {'title': 'Url', 'buttonLabel': 'Manage Urls', 'description': 'Manage Event Urls'}, 'operations': '', 'fields': {'url': {'type': 'String', 'required': True, 'pattern': {'regex': 'main.url', 'message': 'Bad URL format'}}, 'params': {'type': 'JSON', 'required': False}, 'createdAt': {'type': 'ISODate', 'required': True, 'autoGenerate': True, 'ui': {'readOnly': True, 'displayAfterField': '-1'}}, 'updatedAt': {'type': 'ISODate', 'required': True, 'autoUpdate': True, 'ui': {'readOnly': True, 'displayAfterField': '-2'}}}}
    
    class Settings:
        name = "url"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        # Update timestamp fields for auto-updating fields
        current_time = datetime.now(timezone.utc)
        self.updatedAt = current_time
        return await super().save(*args, **kwargs)


class UrlCreate(BaseModel):
    # Fields for create operations
    url: str = Field(..., regex=r"main.url")
    params: dict = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    @validator('url')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'main.url', v):
            raise ValueError("Bad URL format")
        return v
    class Config:
        orm_mode = True


class UrlRead(BaseModel):
    # Fields for read operations
    id: PydanticObjectId = Field(alias="_id")
    url: Optional[str] = Field(None, regex=r"main.url")
    params: Optional[dict] = Field(None)
    createdAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}


