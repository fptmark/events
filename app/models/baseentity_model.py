from beanie import Document

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


class BaseEntityBase(BaseModel):
    _id: PydanticObjectId = Field(default_factory=datetime.utcnow)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)



class BaseEntity(Document, BaseEntityBase):
    class Settings:
        name = "baseentity"

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class BaseEntityCreate(BaseEntityBase):
    class Config:
        orm_mode = True


class BaseEntityRead(BaseEntityBase):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}