
from app.models.baseentity_model import BaseEntity, BaseEntityCreate, BaseEntityRead

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

class User(BaseEntity):
    # User-specific fields
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)

    
    # Class-level metadata for UI generation
    __ui_metadata__: ClassVar[Dict[str, Any]] = {'entity': 'User', 'displayName': 'User', 'fields': {'username': {'type': 'String', 'displayName': 'Username', 'display': 'always', 'displayAfterField': '', 'widget': 'text', 'required': True, 'minLength': 3, 'maxLength': 50}, 'email': {'type': 'String', 'displayName': 'Email', 'display': 'always', 'displayAfterField': 'username', 'widget': 'text', 'required': True, 'minLength': 8, 'maxLength': 50, 'pattern': '^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$'}, 'password': {'type': 'String', 'displayName': 'Password', 'display': 'form', 'displayAfterField': 'email', 'widget': 'text', 'required': True, 'minLength': 8}, 'firstName': {'type': 'String', 'displayName': 'First Name', 'display': 'always', 'displayAfterField': 'password', 'widget': 'text', 'required': True, 'minLength': 3, 'maxLength': 100}, 'lastName': {'type': 'String', 'displayName': 'Last Name', 'display': 'always', 'displayAfterField': 'firstName', 'widget': 'text', 'required': True, 'minLength': 3, 'maxLength': 100}, 'gender': {'type': 'String', 'displayName': 'Gender', 'display': 'always', 'displayAfterField': 'lastName', 'widget': 'select', 'required': False, 'options': ['male', 'female', 'other']}, 'isAccountOwner': {'type': 'Boolean', 'displayName': 'Is Account Owner', 'display': 'always', 'displayAfterField': 'gender', 'widget': 'checkbox', 'required': True}, 'accountId': {'type': 'ObjectId', 'displayName': 'Account ID', 'display': 'always', 'displayAfterField': 'isAccountOwner', 'widget': 'reference', 'required': True}}}
    
    class Settings:
        name = "user"
    
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get UI metadata for this entity."""
        return cls.__ui_metadata__

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class UserCreate(BaseEntityCreate):
    # User-specific fields
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(...)
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
        _custom = {"pattern": "Bad email address format"}
        if v is not None and len(v) < 8:
            raise ValueError("email must be at least 8 characters")
        if v is not None and len(v) > 50:
            raise ValueError("email must be at most 50 characters")
        if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError(_custom["pattern"])
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
        _custom = {"enum": "must be male or female"}
        allowed = ["male", "female", "other"]
        if v is not None and v not in allowed:
            raise ValueError(_custom["enum"])
        return v
    class Config:
        orm_mode = True


class UserRead(BaseEntityRead):
    # User-specific fields
    username: str = Field(None, min_length=3, max_length=50)
    email: str = Field(None, min_length=8, max_length=50)
    password: str = Field(None, min_length=8)
    firstName: str = Field(None, min_length=3, max_length=100)
    lastName: str = Field(None, min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(None)
    accountId: PydanticObjectId = Field(None)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}

