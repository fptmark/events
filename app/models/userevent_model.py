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


class UserEvent(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'attended': {'type': 'Boolean', 'required': False},
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
    'ui': {'title': 'User Events', 'buttonLabel': 'Manage Event Attendance'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "userevent"

    model_config = ConfigDict(
        populate_by_name=True,
    )

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
     

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await DatabaseFactory.find_all("userevent", cls)
        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "find_all")

    @classmethod
    def find(cls):
        class FindAdapter:
            @staticmethod
            async def to_list():
                return await cls.find_all()

        return FindAdapter()

    @classmethod
    async def get(cls, id: str) -> Self:
        try:
            userevent = await DatabaseFactory.get_by_id("userevent", str(id), cls)
            if not userevent:
                raise NotFoundError("UserEvent", id)
            return userevent
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "get")

    async def save(self, doc_id: Optional[str] = None) -> Self:
        try:
            self.updatedAt = datetime.now(timezone.utc)
            if doc_id:
                self.id = doc_id

            data = self.model_dump(exclude={"id"})
            
            # Get unique constraints from metadata
            unique_constraints = self._metadata.get('uniques', [])
            
            # Save document with unique constraints
            result = await DatabaseFactory.save_document("userevent", self.id, data, unique_constraints)
            
            # Update ID from result
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

            return self
        except ValidationError:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "save")
            
    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete userevent without ID",
                entity="UserEvent",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("userevent", self.id)
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

