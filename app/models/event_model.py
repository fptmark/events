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


class EventBase(BaseModel):
    url: str = Field(...)
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[str] = Field(None)

    @validator('url')
    def validate_url(cls, v):
        _custom = {"pattern": "Bad URL format"}
        if not re.match(r'^https?://[^\s]+$', v):
            raise ValueError(_custom["pattern"])
        return v
    @validator('recurrence')
    def validate_recurrence(cls, v):
        _custom = {}
        allowed = ["daily", "weekly", "monthly", "yearly"]
        if v not in allowed:
            raise ValueError("recurrence must be one of " + ", ".join(allowed))
        return v


class Event(BaseEntity, EventBase):
    class Settings:
        name = "event"

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class EventCreate(EventBase):
    class Config:
        orm_mode = True


class EventRead(EventBase):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}