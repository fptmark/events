

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, ClassVar
from datetime import datetime, timezone
import re
import json

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"

class User(Document):
    # Base fields
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, regex=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accountId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'User', 'ui': {'title': 'Users', 'buttonLabel': 'Manage Users', 'description': 'Manage User Profile'}, 'operations': ['rcu'], 'fields': {'username': {'type': 'String', 'required': True, 'minLength': 3, 'maxLength': 50}, 'email': {'type': 'String', 'required': True, 'minLength': 8, 'maxLength': 50, 'pattern': {'regex': '^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', 'message': 'Bad email address format'}}, 'password': {'type': 'String', 'required': True, 'minLength': 8, 'ui': {'displayPages': 'details', 'display': 'secret'}}, 'firstName': {'type': 'String', 'required': True, 'minLength': 3, 'maxLength': 100, 'ui': {'displayName': 'First Name'}}, 'lastName': {'type': 'String', 'required': True, 'minLength': 3, 'maxLength': 100, 'ui': {'displayName': 'Last Name'}}, 'gender': {'type': 'String', 'required': False, 'enum': {'values': ['male', 'female', 'other'], 'message': 'must be male or female'}}, 'dob': {'type': 'ISODate'}, 'isAccountOwner': {'type': 'Boolean', 'required': True, 'ui': {'displayName': 'Owner'}}, 'createdAt': {'type': 'ISODate', 'required': True, 'autoGenerate': True, 'ui': {'readOnly': True, 'displayAfterField': '-1', 'displayPages': 'summary'}}, 'updatedAt': {'type': 'ISODate', 'required': True, 'autoUpdate': True, 'ui': {'displayAfterField': '-2'}}, 'accountId': {'type': 'ObjectId', 'required': True, 'displayName': 'Account ID', 'readOnly': True}}}
    
    class Settings:
        name = "user"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        # Update timestamp fields for auto-updating fields
        current_time = datetime.now(timezone.utc)
        self.updatedAt = current_time
        return await super().save(*args, **kwargs)


class UserCreate(BaseModel):
    # Fields for create operations
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, regex=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accountId: PydanticObjectId = Field(...)
    @validator('username')
    def validate_username(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError("username must be at least 3 characters")
        if v is not None and len(v) > 50:
            raise ValueError("username must be at most 50 characters")
        return v
    @validator('email')
    def validate_email(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError("email must be at least 8 characters")
        if v is not None and len(v) > 50:
            raise ValueError("email must be at most 50 characters")
        if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError("Bad email address format")
        return v
    @validator('password')
    def validate_password(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v
    @validator('firstName')
    def validate_firstName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError("firstName must be at least 3 characters")
        if v is not None and len(v) > 100:
            raise ValueError("firstName must be at most 100 characters")
        return v
    @validator('lastName')
    def validate_lastName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError("lastName must be at least 3 characters")
        if v is not None and len(v) > 100:
            raise ValueError("lastName must be at most 100 characters")
        return v
    @validator('gender')
    def validate_gender(cls, v):
        _custom = {}
        allowed = ["male", "female", "other"]
        if v is not None and v not in allowed:
            raise ValueError("must be male or female")
        return v
    class Config:
        orm_mode = True


class UserRead(BaseModel):
    # Fields for read operations
    id: Optional[PydanticObjectId] = Field(alias="_id")
    username: str = Field(None, min_length=3, max_length=50)
    email: str = Field(None, min_length=8, max_length=50, regex=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(None, min_length=8)
    firstName: str = Field(None, min_length=3, max_length=100)
    lastName: str = Field(None, min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accountId: PydanticObjectId = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}


