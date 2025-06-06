from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from app.db import Database
import app.utils as helpers
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class Url(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    params: Optional[Dict[str, Any]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
 
    _metadata: ClassVar[Dict[str, Any]] = {   'entity': 'Url',
    'fields': {   'url': {   'type': 'String',
                             'required': True,
                             'pattern': {   'regex': '^https?://[^s]+$',
                                            'message': 'Bad URL format'}},
                  'params': {'type': 'JSON', 'required': False},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}}},
    'operations': '',
    'ui': {   'title': 'Url',
              'buttonLabel': 'Manage Urls',
              'description': 'Manage Event Urls'}}

    class Settings:
        name = "url"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('url')
    def validate_url(cls, v: str) -> str:
        if not re.match(r'^https?://[^s]+$', v):
            raise ValidationError(
                message="Invalid URL format",
                entity="Url",
                invalid_fields=[ValidationFailure("url", "URL must start with http:// or https://", v)]
            )
        return v

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)
 
    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await Database.find_all("url", cls)
        except Exception as e:
            raise DatabaseError(str(e), "Url", "find_all")

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

    @classmethod
    async def get(cls, id: str) -> Self:
        try:
            url = await Database.get_by_id("url", str(id), cls)
            if not url:
                raise NotFoundError("Url", id)
            return url
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Url", "get")

    async def save(self) -> Self:
        try:
            # Update timestamp
            self.updatedAt = datetime.now(timezone.utc)

            # Convert model to dict
            data = self.model_dump(exclude={"id"})

            # Save document
            result = await Database.save_document("url", self.id, data)

            # Update ID if this was a new document
            if not self.id and result and isinstance(result, dict) and result.get("_id"):
                self.id = result["_id"]

            return self
        except Exception as e:
            raise DatabaseError(str(e), "Url", "save")

    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete URL without ID",
                entity="Url",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await Database.delete_document("url", self.id)
            if not result:
                raise NotFoundError("Url", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Url", "delete")

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UrlCreate(BaseModel):
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
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
