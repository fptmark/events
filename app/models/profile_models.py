from pydantic import BaseModel, Field

class Profile(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str
    name: str
    preferences: dict
    radius: int
