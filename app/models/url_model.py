from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Url(BaseEntity):
    url: str = Field(..., regex=r'^https?')
    params: Optional[dict] = Field(None)

    class Settings:
        name = "url"

    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)

class UrlCreate(BaseModel):
    url: str = Field(..., regex=r'^https?')
    params: Optional[dict] = Field(None)
    class Config:
        orm_mode = True

class UrlRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    url: str = Field(..., regex=r'^https?')
    params: Optional[dict] = Field(None)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}