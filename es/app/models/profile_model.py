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


class Profile(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(..., max_length=100)
    preferences: Optional[str] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
 
    _metadata: ClassVar[Dict[str, Any]] = {   'entity': 'Profile',
    'fields': {   'name': {   'type': 'String',
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
              'description': 'Manage User Preferences'}}

    class Settings:
        name = "profile"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        if len(v) > 100:
            raise ValidationError(
                message="Name too long",
                entity="Profile",
                invalid_fields=[ValidationFailure("name", "Name must be at most 100 characters", v)]
            )
        return v

    @field_validator('radiusMiles')
    def validate_radiusMiles(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValidationError(
                message="Invalid radius",
                entity="Profile",
                invalid_fields=[ValidationFailure("radiusMiles", "Radius must be at least 0 miles", v)]
            )
        return v

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)
 
    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await Database.find_all("profile", cls)
        except Exception as e:
            raise DatabaseError(str(e), "Profile", "find_all")

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
            profile = await Database.get_by_id("profile", str(id), cls)
            if not profile:
                raise NotFoundError("Profile", id)
            return profile
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Profile", "get")

    async def save(self) -> Self:
        try:
            # Update timestamp
            self.updatedAt = datetime.now(timezone.utc)

            # Convert model to dict
            data = self.model_dump(exclude={"id"})

            # Save document
            result = await Database.save_document("profile", self.id, data)

            # Update ID if this was a new document
            if not self.id and result and isinstance(result, dict) and result.get("_id"):
                self.id = result["_id"]

            return self
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
            result = await Database.delete_document("profile", self.id)
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

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProfileRead(BaseModel):
    id: str = Field(alias="_id")
    name: str = Field(..., max_length=100)
    preferences: Optional[str] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: str = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
