from pydantic import BaseModel, Field

class UserEvent(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str
    eventId: str
    attended: bool
    rating: int
    note: str
