

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

class Account(Document):
    # Base fields
    expiredAt: Optional[datetime] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Account', 'displayName': 'Account', 'fields': {'expiredAt': {'type': 'ISODate', 'required': False, 'displayName': 'Expired At'}, 'createdAt': {'type': 'ISODate', 'readOnly': True, 'displayAfterField': '-1', 'required': True, 'autoGenerate': True, 'displayName': 'Created At'}, 'updatedAt': {'type': 'ISODate', 'required': True, 'autoUpdate': True, 'displayAfterField': 'createdAt', 'display': 'details', 'displayName': 'Updated At'}}}
    
    class Settings:
        name = "account"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        # Update timestamp fields for auto-updating fields
        current_time = datetime.now(timezone.utc)
        self.updatedAt = current_time
        return await super().save(*args, **kwargs)


class AccountCreate(BaseModel):
    # Fields for create operations
    expiredAt: Optional[datetime] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    class Config:
        orm_mode = True


class AccountRead(BaseModel):
    # Fields for read operations
    id: Optional[PydanticObjectId] = Field(alias="_id")
    expiredAt: Optional[datetime] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}


