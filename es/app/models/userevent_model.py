from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from app.db import Database
import app.utils as helpers
from ..errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class UserEvent(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
 
    _metadata: ClassVar[Dict[str, Any]] = {   'entity': 'UserEvent',
    'fields': {   'attended': {'type': 'Boolean', 'required': False},
                  'rating': {   'type': 'Integer',
                                'required': False,
                                'ge': 1,
                                'le': 5},
                  'note': {   'type': 'String',
                              'required': False,
                              'max_length': 500,
                              'ui': {'displayPages': 'details'}},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}},
                  'userId': {'type': 'ObjectId', 'required': True},
                  'eventId': {'type': 'ObjectId', 'required': True}},
    'operations': '',
    'ui': {'title': 'User Events', 'buttonLabel': 'Manage Event Attendance'}}

    class Settings:
        name = "userevent"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('rating')
    def validate_rating(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 1:
                raise ValidationError(
                    message="Invalid rating value",
                    entity="UserEvent",
                    invalid_fields=[ValidationFailure("rating", "Rating must be at least 1", v)]
                )
            if v > 5:
                raise ValidationError(
                    message="Invalid rating value",
                    entity="UserEvent",
                    invalid_fields=[ValidationFailure("rating", "Rating must be at most 5", v)]
                )
        return v

    @field_validator('note')
    def validate_note(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 500:
            raise ValidationError(
                message="Note too long",
                entity="UserEvent",
                invalid_fields=[ValidationFailure("note", "Note must be at most 500 characters", v)]
            )
        return v

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)
 
    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await Database.find_all("userevent", cls)
        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "find_all")

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
            userevent = await Database.get_by_id("userevent", str(id), cls)
            if not userevent:
                raise NotFoundError("UserEvent", id)
            return userevent
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "get")

    async def save(self) -> Self:
        try:
            # Update timestamp
            self.updatedAt = datetime.now(timezone.utc)

            # Convert model to dict
            data = self.model_dump(exclude={"id"})

            # Save document
            result = await Database.save_document("userevent", self.id, data)

            # Update ID if this was a new document
            if not self.id and result and isinstance(result, dict) and result.get("_id"):
                self.id = result["_id"]

            return self
        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "save")

    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete user event without ID",
                entity="UserEvent",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await Database.delete_document("userevent", self.id)
            if not result:
                raise NotFoundError("UserEvent", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "delete")

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserEventCreate(BaseModel):
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)

    @field_validator('rating', mode='before')
    def validate_rating(cls, v):
        if v is not None and int(v) < 1:
            raise ValueError('rating must be at least 1')
        if v is not None and int(v) > 5:
            raise ValueError('rating must be at most 5')
        return v
     
    @field_validator('note', mode='before')
    def validate_note(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('note must be at most 500 characters')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserEventUpdate(BaseModel):
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)

    @field_validator('rating', mode='before')
    def validate_rating(cls, v):
        if v is not None and int(v) < 1:
            raise ValueError('rating must be at least 1')
        if v is not None and int(v) > 5:
            raise ValueError('rating must be at most 5')
        return v
     
    @field_validator('note', mode='before')
    def validate_note(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('note must be at most 500 characters')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserEventRead(BaseModel):
    id: str = Field(alias="_id")
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
