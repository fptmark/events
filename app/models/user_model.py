from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
        super().__init__(f"Unique constraint violated for fields: {', '.join(fields)}")

class User(BaseEntity):
    accountId: PydanticObjectId = Field(...)
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, regex=r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., max_length=100)
    lastName: str = Field(..., max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(...)

    class Settings:
        name = "user"

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
    email: str = Field(..., min_length=8, max_length=50, regex=r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
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
    email: str = Field(..., min_length=8, max_length=50, regex=r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., max_length=100)
    lastName: str = Field(..., max_length=100)
    gender: Optional[str] = Field(None, description="Allowed values: ['male', 'female', 'other']")
    isAccountOwner: bool = Field(...)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}