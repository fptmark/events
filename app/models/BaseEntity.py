
from beanie import Document, PydanticObjectId
from pydantic import Field
from typing import Optional
from datetime import datetime

class BaseEntity(Document):
    """
    Base entity that auto-manages _id, createdAt, and updatedAt.
    If autoUpdate is true for updatedAt, save() is overridden to update it.
    """

    _id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId)

    createdAt: datetime = Field(default_factory=datetime.utcnow)

    updatedAt: Optional[datetime] = Field(None)

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.utcnow()
        return await super().save(*args, **kwargs)

    class Settings:
        name = None  # Not a real collection