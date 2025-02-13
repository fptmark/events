
from beanie import Document, PydanticObjectId
from pydantic import Field
from typing import Optional
from datetime import datetime, timezone

class BaseEntity(Document):
    """
    Base entity that auto-manages _id, createdAt, and updatedAt.
    If autoUpdate is true for updatedAt, save() is overridden to update it.
    """

    _id: Optional[PydanticObjectId] = Field(default_factory=PydanticObjectId)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    updatedAt: Optional[datetime] = Field(None)

    async def save(self, *args, **kwargs):
        self.updatedAt = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)

    class Settings:
        name = None  # Not a real collection