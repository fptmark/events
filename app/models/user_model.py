from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re
import json

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
        super().__init__(f"Unique constraint violated for fields: {', '.join(fields)}")

class User(BaseEntity):
    accountId: PydanticObjectId = Field(...)
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., max_length=100)
    lastName: str = Field(..., max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(...)

    class Settings:
        name = "user"

    @validator('email')
    def validate_email(cls, v):
        _custom = {"pattern": "Bad email address format"}
        if len(v) < 8:
            raise ValueError("email must be at least 8 characters")
        if len(v) > 50:
            raise ValueError("email must be at most 50 characters")
        if not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError(_custom["pattern"])
        return v
    @validator('gender')
    def validate_gender(cls, v):
        _custom = {"enum": "must be male or female"}
        allowed = ["male", "female", "other"]
        if v not in allowed:
            raise ValueError(_custom["enum"])
        return v

    async def validate_uniques(self):
        # Unique constraint on fields: username
        query = {
            "username": self.username,
        }
        existing = await self.__class__.find_one(query)
        if existing:
            raise UniqueValidationError(["username"], query)
        # Unique constraint on fields: email
        query = {
            "email": self.email,
        }
        existing = await self.__class__.find_one(query)
        if existing:
            raise UniqueValidationError(["email"], query)

    async def save(self, *args, **kwargs):
        await self.validate_uniques()
        return await super().save(*args, **kwargs)

class UserCreate(BaseModel):
    accountId: PydanticObjectId = Field(...)
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., max_length=100)
    lastName: str = Field(..., max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(...)
    class Config:
        orm_mode = True

class UserRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    accountId: PydanticObjectId = Field(...)
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., max_length=100)
    lastName: str = Field(..., max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(...)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}