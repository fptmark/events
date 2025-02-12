from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re
import json


class Userevent(BaseEntity):
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)

    class Settings:
        name = "userevent"


    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)

class UsereventCreate(BaseModel):
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    class Config:
        orm_mode = True

class UsereventRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}