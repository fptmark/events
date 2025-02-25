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


class CrawlBase(BaseModel):
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[dict] = Field(None)
    errorsEncountered: Optional[str] = Field(None)
    urlId: PydanticObjectId = Field(...)



class Crawl(BaseEntity, CrawlBase):
    class Settings:
        name = "crawl"

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)


class CrawlCreate(CrawlBase):
    class Config:
        orm_mode = True


class CrawlRead(CrawlBase):
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}