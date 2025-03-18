
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

class Account(BaseEntity):
    # Account-specific fields
    expiredAt: Optional[datetime] = Field(None)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'Account', 'displayName': 'Account', 'fields': {'expiredAt': {'type': 'ISODate', 'displayName': 'Expired At', 'display': 'always', 'displayAfterField': '', 'widget': 'date', 'required': False}}}
    
    class Settings:
        name = "account"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class AccountCreate(BaseEntityCreate):
    # Account-specific fields
    expiredAt: Optional[datetime] = Field(None)
    class Config:
        orm_mode = True


class AccountRead(BaseEntityRead):
    # Account-specific fields
    expiredAt: Optional[datetime] = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}

