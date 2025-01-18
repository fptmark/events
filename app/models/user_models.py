from pydantic import BaseModel, Field
from datetime import datetime

class User(BaseModel):
    id: str = Field(..., alias="_id")
    accountId: str
    username: str
    password: str
    isOwner: bool
    createdAt: datetime
