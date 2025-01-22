from beanie import Document
from pydantic import Field
from typing import Optional, List, Dict
from datetime import datetime

class Account(Document):
    _id: Optional[str] = Field(None, alias="_id")
    expiredAt: Optional[str] = Field(None)
    createdAt: Optional[str] = Field(None)
