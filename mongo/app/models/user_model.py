from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, ClassVar, Self
from collections.abc import Sequence
from datetime import datetime, timezone
import re
import app.utils as helpers

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"

class User(Document):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'User',
    'fields': {   'accountId': {   'displayName': 'accountId',
                                   'readOnly': True,
                                   'required': True,
                                   'type': 'ObjectId'},
                  'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'displayPages': 'summary',
                                             'readOnly': True}},
                  'dob': {'required': False, 'type': 'ISODate'},
                  'email': {   'max_length': 50,
                               'min_length': 8,
                               'pattern': {   'message': 'Bad email address '
                                                         'format',
                                              'regex': '^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$'},
                               'required': True,
                               'type': 'String'},
                  'firstName': {   'max_length': 100,
                                   'min_length': 3,
                                   'required': True,
                                   'type': 'String',
                                   'ui': {'displayName': 'First Name'}},
                  'gender': {   'enum': {   'message': 'must be male or female',
                                            'values': [   'male',
                                                          'female',
                                                          'other']},
                                'required': False,
                                'type': 'String'},
                  'isAccountOwner': {   'required': True,
                                        'type': 'Boolean',
                                        'ui': {'displayName': 'Owner'}},
                  'lastName': {   'max_length': 100,
                                  'min_length': 3,
                                  'required': True,
                                  'type': 'String',
                                  'ui': {'displayName': 'Last Name'}},
                  'password': {   'min_length': 8,
                                  'required': True,
                                  'type': 'String',
                                  'ui': {   'display': 'secret',
                                            'displayPages': 'details'}},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'username': {   'max_length': 50,
                                  'min_length': 3,
                                  'required': True,
                                  'type': 'String'}},
    'operations': 'rcu',
    'ui': {   'buttonLabel': 'Manage Users',
              'description': 'Manage User Profile',
              'title': 'Users'}}

    class Settings:
        name = "user"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        return await cls.find().to_list()

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)

    @field_validator('username', mode='before')
    def validate_username(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if v is not None and len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v
     
    @field_validator('email', mode='before')
    def validate_email(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if v is not None and len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v
     
    @field_validator('password', mode='before')
    def validate_password(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v
     
    @field_validator('firstName', mode='before')
    def validate_firstName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v
     
    @field_validator('lastName', mode='before')
    def validate_lastName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v
     
    @field_validator('gender', mode='before')
    def validate_gender(cls, v):
        _custom = {}
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
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class UserUpdate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)

    @field_validator('username', mode='before')
    def validate_username(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if v is not None and len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v
     
    @field_validator('email', mode='before')
    def validate_email(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if v is not None and len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v
     
    @field_validator('password', mode='before')
    def validate_password(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v
     
    @field_validator('firstName', mode='before')
    def validate_firstName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v
     
    @field_validator('lastName', mode='before')
    def validate_lastName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v
     
    @field_validator('gender', mode='before')
    def validate_gender(cls, v):
        _custom = {}
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
    
    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

class UserRead(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
            
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={PydanticObjectId: str},
    )
