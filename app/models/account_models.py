from pydantic import BaseModel, Field
from datetime import datetime

class Account(BaseModel):
    id: str = Field(..., alias="_id")
    expiredAt: datetime
    createdAt: datetime
