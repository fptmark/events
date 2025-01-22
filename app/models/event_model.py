from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict

class Event(Document):
    _id: Optional[str] = Field(None, alias="_id")
    url: Optional[str] = Field(None)
    title: Optional[str] = Field(None)
    dateTime: Optional[str] = Field(None)
    location: Optional[str] = Field(None)
    cost: Optional[float] = Field(None)
    numOfExpectedAttendees: Optional[int] = Field(None)
    recurrence: Optional[str] = Field(None)
    tags: Optional[List] = Field(None)
    updatedAt: Optional[str] = Field(None)
