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


class Profile(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., max_length=100)
    preferences: Optional[str] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'name': {   'type': 'String',
                              'required': True,
                              'max_length': 100},
                  'preferences': {   'type': 'String',
                                     'required': False,
                                     'ui': {'displayPages': 'details'}},
                  'radiusMiles': {   'type': 'Integer',
                                     'required': False,
                                     'ge': 0},
                  'userId': {   'type': 'ObjectId',
                                'ui': {   'show': {   'displayInfo': [   {   'displayPages': 'summary',
                                                                             'fields': [   'email']},
                                                                         {   'displayPages': 'details|edit',
                                                                             'fields': [   'email',
                                                                                           'username']}]}},
                                'required': True},
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
    'ui': {   'title': 'Profile',
              'buttonLabel': 'Manage User Profiles',
              'description': 'Manage User Preferences'},
    'services': [],
    'uniques': [['name', 'userId']]}

    class Settings:
        name = "profile"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('name', mode='before')
    def validate_name(cls, v):
        if v is not None and len(v) > 100:
            raise ValueError('name must be at most 100 characters')
        return v
     
    @field_validator('radiusMiles', mode='before')
    def validate_radiusMiles(cls, v):
        if v is not None and int(v) < 0:
            raise ValueError('radiusMiles must be at least 0')
        return v
     

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await DatabaseFactory.find_all("profile", cls)
        except Exception as e:
            raise DatabaseError(str(e), "Profile", "find_all")

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
            profile = await DatabaseFactory.get_by_id("profile", str(id), cls)
            if not profile:
                raise NotFoundError("Profile", id)
            return profile
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Profile", "get")

    async def save(self, doc_id: Optional[str] = None) -> Self:
        try:
            self.updatedAt = datetime.now(timezone.utc)
            if doc_id:
                self.id = doc_id

            data = self.model_dump(exclude={"id"})
            
            # Get unique constraints from metadata
            unique_constraints = self._metadata.get('uniques', [])
            
            # Save document with unique constraints
            result = await DatabaseFactory.save_document("profile", self.id, data, unique_constraints)
            
            # Update ID from result
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

            return self
        except ValidationError:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Profile", "save")
            
    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete profile without ID",
                entity="Profile",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("profile", self.id)
            if not result:
                raise NotFoundError("Profile", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Profile", "delete")

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProfileCreate(BaseModel):
  name: str = Field(..., max_length=100)
  preferences: Optional[str] = Field(None)
  radiusMiles: Optional[int] = Field(None, ge=0)
  userId: str = Field(...)

  @field_validator('name', mode='before')
  def validate_name(cls, v):
      if v is not None and len(v) > 100:
          raise ValueError('name must be at most 100 characters')
      return v
   
  @field_validator('radiusMiles', mode='before')
  def validate_radiusMiles(cls, v):
      if v is not None and int(v) < 0:
          raise ValueError('radiusMiles must be at least 0')
      return v
   

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)


from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProfileUpdate(BaseModel):
  name: str = Field(..., max_length=100)
  preferences: Optional[str] = Field(None)
  radiusMiles: Optional[int] = Field(None, ge=0)
  userId: str = Field(...)

  @field_validator('name', mode='before')
  def validate_name(cls, v):
      if v is not None and len(v) > 100:
          raise ValueError('name must be at most 100 characters')
      return v
   
  @field_validator('radiusMiles', mode='before')
  def validate_radiusMiles(cls, v):
      if v is not None and int(v) < 0:
          raise ValueError('radiusMiles must be at least 0')
      return v
   

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

