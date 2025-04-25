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

class Account(Document):
    expiredAt: Optional[datetime] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Account',
    'fields': {   'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'expiredAt': {'required': False, 'type': 'ISODate'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': 'createdAt',
                                             'displayPages': 'details',
                                             'readOnly': True}}},
    'operations': '',
    'ui': {'buttonLabel': 'Manage Accounts', 'title': 'Accounts'}}

    class Settings:
        name = "account"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class AccountCreate(BaseModel):
    expiredAt: Optional[datetime] = Field(None)

    @validator('expiredAt', pre=True)
    def parse_expiredAt(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    class Config:
        orm_mode = True
        extra = Extra.ignore

class AccountUpdate(BaseModel):
    expiredAt: Optional[datetime] = Field(None)

    @validator('expiredAt', pre=True)
    def parse_expiredAt(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    class Config:
        orm_mode = True
        extra = Extra.ignore

class AccountRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    expiredAt: Optional[datetime] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}
