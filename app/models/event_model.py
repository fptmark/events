from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Event(BaseEntity):
    url: str = Field(..., regex=r'^https?')
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")

    class Settings:
        name = "event"

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)

class EventCreate(BaseModel):
    url: str = Field(..., regex=r'^https?')
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    class Config:
        orm_mode = True

class EventRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    url: str = Field(..., regex=r'^https?')
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description="Allowed values: ['daily', 'weekly', 'monthly', 'yearly']")
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}