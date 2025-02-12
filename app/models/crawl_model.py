from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re
import json


class Crawl(BaseEntity):
    urlId: PydanticObjectId = Field(...)
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)

    class Settings:
        name = "crawl"


    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)

class CrawlCreate(BaseModel):
    urlId: PydanticObjectId = Field(...)
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    class Config:
        orm_mode = True

class CrawlRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    urlId: PydanticObjectId = Field(...)
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}