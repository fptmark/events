from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re
import json


class Url(BaseEntity):
    url: str = Field(...)
    params: Optional[dict] = Field(None)

    class Settings:
        name = "url"

    @validator('url')
    def validate_url(cls, v):
        _custom = {"pattern": "Bad URL format"}
        if not re.match(r'^https?://[^\s]+$', v):
            raise ValueError(_custom["pattern"])
        return v

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)

class UrlCreate(BaseModel):
    url: str = Field(...)
    params: Optional[dict] = Field(None)
    class Config:
        orm_mode = True

class UrlRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    url: str = Field(...)
    params: Optional[dict] = Field(None)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}