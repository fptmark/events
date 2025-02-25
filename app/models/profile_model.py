from .baseentity_model import BaseEntity

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


class ProfileBase(BaseModel):
    name: str = Field(..., max_length=100)
    preferences: Optional[dict] = Field(None)
    radiusMiles: Optional[int] = Field(None, ge=0)
    userId: PydanticObjectId = Field(...)



class Profile(BaseEntity, ProfileBase):
    class Settings:
        name = "profile"

    async def validate_uniques(self):
        query_1 = {
            "name": self.name,
            "userId": self.userId,
        }
        existing_1 = await self.__class__.find_one(query_1)
        if existing_1:
            raise UniqueValidationError(["name", "userId"], query_1)

    async def save(self, *args, **kwargs):
        await self.validate_uniques()
        return await super().save(*args, **kwargs)


class ProfileCreate(ProfileBase):
    class Config:
        orm_mode = True


class ProfileRead(ProfileBase):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}