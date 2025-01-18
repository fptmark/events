from pydantic import BaseModel, Field
from datetime import datetime

class Event(BaseModel):
    id: str = Field(..., alias="_id")
    title: str
    dateTime: datetime
    location: str
    cost: float
    numOfExpectedAttendees: int
    recurrence: str
    tags: list[str]
