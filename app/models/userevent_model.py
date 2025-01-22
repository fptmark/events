from beanie import Document
from pydantic import Field
from typing import Optional, List, Dict
from datetime import datetime

class UserEvent(Document):
    _id: Optional[str] = Field(None, alias="_id")
    userId: Optional[str] = Field(None)
    eventId: Optional[str] = Field(None)
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None)
    note: Optional[str] = Field(None)
    updatedAt: Optional[str] = Field(None)
