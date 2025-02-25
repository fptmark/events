from .baseentity_model import BaseEntity
from app.services.auth.cookies.redis import CookiesAuth as Auth

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re
import json

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)

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


class User(BaseEntity, Auth, UserBase):
    class Settings:
        name = "user"

    async def validate_uniques(self):
        query_1 = {
            "username": self.username,
        }
        existing_1 = await self.__class__.find_one(query_1)
        if existing_1:
            raise UniqueValidationError(["username"], query_1)
        query_2 = {
            "email": self.email,
        }
        existing_2 = await self.__class__.find_one(query_2)
        if existing_2:
            raise UniqueValidationError(["email"], query_2)

    async def save(self, *args, **kwargs):
        await self.validate_uniques()
        return await super().save(*args, **kwargs)


class UserCreate(UserBase):
    class Config:
        orm_mode = True


class UserRead(UserBase):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}