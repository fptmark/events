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

class Profile(BaseEntity):
    userId: PydanticObjectId = Field(...)
    name: str = Field(..., max_length=100)
    preferences: Optional[dict] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)

    class Settings:
        name = "profile"


    async def validate_uniques(self):
        # Unique constraint on fields: name, userId
        query = {
            "name": self.name,
            "userId": self.userId,
        }
        existing = await self.__class__.find_one(query)
        if existing:
            raise UniqueValidationError(["name", "userId"], query)

    async def save(self, *args, **kwargs):
        await self.validate_uniques()
        return await super().save(*args, **kwargs)

class ProfileCreate(BaseModel):
    userId: PydanticObjectId = Field(...)
    name: str = Field(..., max_length=100)
    preferences: Optional[dict] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    class Config:
        orm_mode = True

class ProfileRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    userId: PydanticObjectId = Field(...)
    name: str = Field(..., max_length=100)
    preferences: Optional[dict] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}