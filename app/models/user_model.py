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


class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    netWorth: Optional[float] = Field(None, ge=0, le=10000000)
    accountId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'username': {   'type': 'String',
                                  'required': True,
                                  'min_length': 3,
                                  'max_length': 50},
                  'email': {   'type': 'String',
                               'required': True,
                               'min_length': 8,
                               'max_length': 50,
                               'pattern': {   'regex': '^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$',
                                              'message': 'Bad email address '
                                                         'format'}},
                  'password': {   'type': 'String',
                                  'required': True,
                                  'min_length': 8,
                                  'ui': {   'displayPages': 'details',
                                            'display': 'secret'}},
                  'firstName': {   'type': 'String',
                                   'required': True,
                                   'min_length': 3,
                                   'max_length': 100,
                                   'ui': {'displayName': 'First Name'}},
                  'lastName': {   'type': 'String',
                                  'required': True,
                                  'min_length': 3,
                                  'max_length': 100,
                                  'ui': {'displayName': 'Last Name'}},
                  'gender': {   'type': 'String',
                                'required': False,
                                'enum': {   'values': [   'male',
                                                          'female',
                                                          'other'],
                                            'message': 'must be male or '
                                                       'female'}},
                  'dob': {'type': 'ISODate', 'required': False},
                  'isAccountOwner': {   'type': 'Boolean',
                                        'required': True,
                                        'ui': {'displayName': 'Owner'}},
                  'netWorth': {'type': 'Currency', 'ge': 0, 'le': 10000000},
                  'accountId': {   'type': 'ObjectId',
                                   'ui': {   'displayName': 'Account',
                                             'show': {   'endpoint': 'account',
                                                         'displayInfo': [   {   'displayPages': 'summary',
                                                                                'fields': [   'createdAt']},
                                                                            {   'displayPages': 'edit|create',
                                                                                'fields': [   'createdAt',
                                                                                              'expiredAt']}]}},
                                   'required': True},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1',
                                             'displayPages': 'summary'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}}},
    'operations': 'rcu',
    'ui': {   'title': 'Users',
              'buttonLabel': 'Manage Users',
              'description': 'Manage User Profile'},
    'services': ['auth.cookies.redis'],
    'uniques': [['username'], ['email']]}

    class Settings:
        name = "user"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('username', mode='before')
    def validate_username(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if v is not None and len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v
     
    @field_validator('email', mode='before')
    def validate_email(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if v is not None and len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v
     
    @field_validator('password', mode='before')
    def validate_password(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v
     
    @field_validator('firstName', mode='before')
    def validate_firstName(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v
     
    @field_validator('lastName', mode='before')
    def validate_lastName(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v
     
    @field_validator('gender', mode='before')
    def validate_gender(cls, v):
        allowed = ['male', 'female', 'other']
        if v is not None and v not in allowed:
            raise ValueError('must be male or female')
        return v
     
    @field_validator('dob', mode='before')
    def parse_dob(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    @field_validator('netWorth', mode='before')
    def validate_netWorth(cls, v):
        if v is None: return None
        parsed = helpers.parse_currency(v)
        if parsed is None:
            raise ValueError('netWorth must be a valid currency')
        if parsed < 0:
            raise ValueError('netWorth must be at least 0')
        if parsed > 10000000:
            raise ValueError('netWorth must be at most 10000000')
        return parsed

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await DatabaseFactory.find_all("user", cls)
        except Exception as e:
            raise DatabaseError(str(e), "User", "find_all")

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
            user = await DatabaseFactory.get_by_id("user", str(id), cls)
            if not user:
                raise NotFoundError("User", id)
            return user
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "get")

    async def save(self, doc_id: Optional[str] = None) -> Self:
        try:
            self.updatedAt = datetime.now(timezone.utc)
            if doc_id:
                self.id = doc_id

            data = self.model_dump(exclude={"id"})
            
            # Get unique constraints from metadata
            unique_constraints = self._metadata.get('uniques', [])
            
            # Save document with unique constraints
            result = await DatabaseFactory.save_document("user", self.id, data, unique_constraints)
            
            # Update ID from result
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

            return self
        except ValidationError:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "save")
            
    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete user without ID",
                entity="User",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("user", self.id)
            if not result:
                raise NotFoundError("User", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "delete")

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserCreate(BaseModel):
  username: str = Field(..., min_length=3, max_length=50)
  email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
  password: str = Field(..., min_length=8)
  firstName: str = Field(..., min_length=3, max_length=100)
  lastName: str = Field(..., min_length=3, max_length=100)
  gender: Optional[str] = Field(None, description ="must be male or female")
  dob: Optional[datetime] = Field(None)
  isAccountOwner: bool = Field(...)
  netWorth: Optional[float] = Field(None, ge=0, le=10000000)
  accountId: str = Field(...)

  @field_validator('username', mode='before')
  def validate_username(cls, v):
      if v is not None and len(v) < 3:
          raise ValueError('username must be at least 3 characters')
      if v is not None and len(v) > 50:
          raise ValueError('username must be at most 50 characters')
      return v
   
  @field_validator('email', mode='before')
  def validate_email(cls, v):
      if v is not None and len(v) < 8:
          raise ValueError('email must be at least 8 characters')
      if v is not None and len(v) > 50:
          raise ValueError('email must be at most 50 characters')
      if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
          raise ValueError('Bad email address format')
      return v
   
  @field_validator('password', mode='before')
  def validate_password(cls, v):
      if v is not None and len(v) < 8:
          raise ValueError('password must be at least 8 characters')
      return v
   
  @field_validator('firstName', mode='before')
  def validate_firstName(cls, v):
      if v is not None and len(v) < 3:
          raise ValueError('firstName must be at least 3 characters')
      if v is not None and len(v) > 100:
          raise ValueError('firstName must be at most 100 characters')
      return v
   
  @field_validator('lastName', mode='before')
  def validate_lastName(cls, v):
      if v is not None and len(v) < 3:
          raise ValueError('lastName must be at least 3 characters')
      if v is not None and len(v) > 100:
          raise ValueError('lastName must be at most 100 characters')
      return v
   
  @field_validator('gender', mode='before')
  def validate_gender(cls, v):
      allowed = ['male', 'female', 'other']
      if v is not None and v not in allowed:
          raise ValueError('must be male or female')
      return v
   
  @field_validator('dob', mode='before')
  def parse_dob(cls, v):
      if v in (None, '', 'null'):
          return None
      if isinstance(v, str):
          return datetime.fromisoformat(v)
      return v
  @field_validator('netWorth', mode='before')
  def validate_netWorth(cls, v):
      if v is None: return None
      parsed = helpers.parse_currency(v)
      if parsed is None:
          raise ValueError('netWorth must be a valid currency')
      if parsed < 0:
          raise ValueError('netWorth must be at least 0')
      if parsed > 10000000:
          raise ValueError('netWorth must be at most 10000000')
      return parsed

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)


from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserUpdate(BaseModel):
  username: str = Field(..., min_length=3, max_length=50)
  email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
  password: str = Field(..., min_length=8)
  firstName: str = Field(..., min_length=3, max_length=100)
  lastName: str = Field(..., min_length=3, max_length=100)
  gender: Optional[str] = Field(None, description ="must be male or female")
  dob: Optional[datetime] = Field(None)
  isAccountOwner: bool = Field(...)
  netWorth: Optional[float] = Field(None, ge=0, le=10000000)
  accountId: str = Field(...)

  @field_validator('username', mode='before')
  def validate_username(cls, v):
      if v is not None and len(v) < 3:
          raise ValueError('username must be at least 3 characters')
      if v is not None and len(v) > 50:
          raise ValueError('username must be at most 50 characters')
      return v
   
  @field_validator('email', mode='before')
  def validate_email(cls, v):
      if v is not None and len(v) < 8:
          raise ValueError('email must be at least 8 characters')
      if v is not None and len(v) > 50:
          raise ValueError('email must be at most 50 characters')
      if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
          raise ValueError('Bad email address format')
      return v
   
  @field_validator('password', mode='before')
  def validate_password(cls, v):
      if v is not None and len(v) < 8:
          raise ValueError('password must be at least 8 characters')
      return v
   
  @field_validator('firstName', mode='before')
  def validate_firstName(cls, v):
      if v is not None and len(v) < 3:
          raise ValueError('firstName must be at least 3 characters')
      if v is not None and len(v) > 100:
          raise ValueError('firstName must be at most 100 characters')
      return v
   
  @field_validator('lastName', mode='before')
  def validate_lastName(cls, v):
      if v is not None and len(v) < 3:
          raise ValueError('lastName must be at least 3 characters')
      if v is not None and len(v) > 100:
          raise ValueError('lastName must be at most 100 characters')
      return v
   
  @field_validator('gender', mode='before')
  def validate_gender(cls, v):
      allowed = ['male', 'female', 'other']
      if v is not None and v not in allowed:
          raise ValueError('must be male or female')
      return v
   
  @field_validator('dob', mode='before')
  def parse_dob(cls, v):
      if v in (None, '', 'null'):
          return None
      if isinstance(v, str):
          return datetime.fromisoformat(v)
      return v
  @field_validator('netWorth', mode='before')
  def validate_netWorth(cls, v):
      if v is None: return None
      parsed = helpers.parse_currency(v)
      if parsed is None:
          raise ValueError('netWorth must be a valid currency')
      if parsed < 0:
          raise ValueError('netWorth must be at least 0')
      if parsed > 10000000:
          raise ValueError('netWorth must be at most 10000000')
      return parsed

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

