
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

class Url(BaseEntity):
    # Url-specific fields
    url: str = Field(...)
    params: Optional[dict] = Field(None)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Url', 'displayName': 'Url', 'fields': {'url': {'type': 'String', 'displayName': 'Url', 'display': 'always', 'displayAfterField': '', 'widget': 'text', 'required': True, 'pattern': '^https?://[^s]+$'}, 'params': {'type': 'JSON', 'displayName': 'Params', 'display': 'always', 'displayAfterField': 'url', 'widget': 'jsoneditor', 'required': False}}}
    
    class Settings:
        name = "url"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class UrlCreate(BaseEntityCreate):
    # Url-specific fields
    url: str = Field(...)
    params: Optional[dict] = Field(None)
    @validator('url')
    def validate_url(cls, v):
        _custom = {"pattern": "Bad URL format"}
        if v is not None and not re.match(r'^https?://[^s]+$', v):
            raise ValueError(_custom["pattern"])
        return v
    class Config:
        orm_mode = True


class UrlRead(BaseEntityRead):
    # Url-specific fields
    url: str = Field(None)
    params: Optional[dict] = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}

