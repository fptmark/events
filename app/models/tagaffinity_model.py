from .BaseEntity import BaseEntity
from beanie import PydanticObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
        super().__init__(f"Unique constraint violated for fields: {', '.join(fields)}")

class Tagaffinity(BaseEntity):
    profileId: PydanticObjectId = Field(...)
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)

    class Settings:
        name = "tagaffinity"

    async def validate_uniques(self):
        # Unique constraint on fields: profileId, tag
        query = {
            "profileId": self.profileId,
            "tag": self.tag,
        }
        existing = await self.__class__.find_one(query)
        if existing:
            raise UniqueValidationError(["profileId", "tag"], query)

    async def save(self, *args, **kwargs):
        await self.validate_uniques()
        return await super().save(*args, **kwargs)

class TagaffinityCreate(BaseModel):
    profileId: PydanticObjectId = Field(...)
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    class Config:
        orm_mode = True

class TagaffinityRead(BaseModel):
    id: Optional[PydanticObjectId] = Field(None, alias="_id")
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    profileId: PydanticObjectId = Field(...)
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        json_encoders = {PydanticObjectId: str}