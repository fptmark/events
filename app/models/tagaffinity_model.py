from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from app.db import DatabaseFactory
import app.utils as helpers
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class TagAffinity(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
 
    _metadata: ClassVar[Dict[str, Any]] = {   'entity': 'TagAffinity',
    'fields': {   'tag': {'type': 'String', 'required': True, 'max_length': 50},
                  'affinity': {   'type': 'Integer',
                                  'required': True,
                                  'ge': -100,
                                  'le': 100},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}},
                  'profileId': {'type': 'ObjectId', 'required': True}},
    'operations': '',
    'ui': {'title': 'Tag Affinity', 'buttonLabel': 'Manage Event Affinity'}}

    class Settings:
        name = "tagaffinity"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('tag')
    def validate_tag(cls, v: str) -> str:
        if len(v) > 50:
            raise ValidationError(
                message="Tag too long",
                entity="TagAffinity",
                invalid_fields=[ValidationFailure("tag", "Tag must be at most 50 characters", v)]
            )
        return v

    @field_validator('affinity')
    def validate_affinity(cls, v: int) -> int:
        if v < -100:
            raise ValidationError(
                message="Invalid affinity value",
                entity="TagAffinity",
                invalid_fields=[ValidationFailure("affinity", "Affinity must be at least -100", v)]
            )
        if v > 100:
            raise ValidationError(
                message="Invalid affinity value",
                entity="TagAffinity",
                invalid_fields=[ValidationFailure("affinity", "Affinity must be at most 100", v)]
            )
        return v

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)
 
    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await DatabaseFactory.find_all("tagaffinity", cls)
        except Exception as e:
            raise DatabaseError(str(e), "TagAffinity", "find_all")

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
            tagaffinity = await DatabaseFactory.get_by_id("tagaffinity", str(id), cls)
            if not tagaffinity:
                raise NotFoundError("TagAffinity", id)
            return tagaffinity
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "TagAffinity", "get")

    async def save(self) -> Self:
        try:
            # Update timestamp
            self.updatedAt = datetime.now(timezone.utc)

            # Convert model to dict
            data = self.model_dump(exclude={"id"})

            # Save document
            result = await DatabaseFactory.save_document("tagaffinity", self.id, data)

            # Update ID if this was a new document
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

            return self
        except Exception as e:
            raise DatabaseError(str(e), "TagAffinity", "save")

    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete tag affinity without ID",
                entity="TagAffinity",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("tagaffinity", self.id)
            if not result:
                raise NotFoundError("TagAffinity", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "TagAffinity", "delete")

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class TagAffinityCreate(BaseModel):
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)

    @field_validator('tag', mode='before')
    def validate_tag(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError('tag must be at most 50 characters')
        return v
     
    @field_validator('affinity', mode='before')
    def validate_affinity(cls, v):
        if v is not None and int(v) < -100:
            raise ValueError('affinity must be at least -100')
        if v is not None and int(v) > 100:
            raise ValueError('affinity must be at most 100')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class TagAffinityUpdate(BaseModel):
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)

    @field_validator('tag', mode='before')
    def validate_tag(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError('tag must be at most 50 characters')
        return v
     
    @field_validator('affinity', mode='before')
    def validate_affinity(cls, v):
        if v is not None and int(v) < -100:
            raise ValueError('affinity must be at least -100')
        if v is not None and int(v) > 100:
            raise ValueError('affinity must be at most 100')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class TagAffinityRead(BaseModel):
    id: str = Field(alias="_id")
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
