from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re
import json


class Account(BaseEntity):
    expiredAt: Optional[datetime] = Field(None)

    class Settings:
        name = "account"


    async def save(self, *args, **kwargs):
        return await super().save(*args, **kwargs)

class AccountCreate(BaseModel):
    expiredAt: Optional[datetime] = Field(None)
    class Config:
        orm_mode = True

class AccountRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    expiredAt: Optional[datetime] = Field(None)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}