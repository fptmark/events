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


class TagAffinityBase(BaseModel):
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: PydanticObjectId = Field(...)



class TagAffinity(BaseEntity, TagAffinityBase):
    class Settings:
        name = "tagaffinity"

    async def validate_uniques(self):
        query_1 = {
            "profileId": self.profileId,
            "tag": self.tag,
        }
        existing_1 = await self.__class__.find_one(query_1)
        if existing_1:
            raise UniqueValidationError(["profileId", "tag"], query_1)

    async def save(self, *args, **kwargs):
        await self.validate_uniques()
        return await super().save(*args, **kwargs)


class TagAffinityCreate(TagAffinityBase):
    class Config:
        orm_mode = True


class TagAffinityRead(TagAffinityBase):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}