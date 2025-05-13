from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from elasticsearch import NotFoundError
import re
from app.db import Database
import app.utils as helpers

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class Url(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    url: str = Field(..., pattern=r"main.url")
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

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)
 
    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        return await Database.find_all("url", cls)

    # Method to imitate Beanie's find() method
    @classmethod
    def find(cls):
        # This is a simple adapter to keep the API compatible
        # It provides a to_list() method that calls find_all()
        class FindAdapter:
            @staticmethod
            async def to_list():
                return await cls.find_all()

        return FindAdapter()

    # Replaces Beanie's get - uses common Database function
    @classmethod
    async def get(cls, id) -> Optional[Self]:
        return await Database.get_by_id("url", str(id), cls)

    # Replaces Beanie's save - uses common Database function
    async def save(self, *args, **kwargs):
        # Update timestamp
        self.updatedAt = datetime.now(timezone.utc)

        # Convert model to dict
        data = self.model_dump(exclude={"id"})

        # Save document using common function
        result = await Database.save_document("url", self.id, data)

        # Update ID if this was a new document
        if not self.id and result and isinstance(result, dict) and result.get("_id"):
            self.id = result["_id"]

        return self

    # Replaces Beanie's delete - uses common Database function
    async def delete(self):
        if self.id:
            return await Database.delete_document("url", self.id)
        return False

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UrlCreate(BaseModel):
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UrlUpdate(BaseModel):
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UrlRead(BaseModel):
    id: str = Field(alias="_id")
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
