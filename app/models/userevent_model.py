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


class UserEventBase(BaseModel):
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)



class UserEvent(BaseEntity, UserEventBase):
    class Settings:
        name = "userevent"

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class UserEventCreate(UserEventBase):
    class Config:
        orm_mode = True


class UserEventRead(UserEventBase):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}