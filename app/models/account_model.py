from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict

class Account(Document):
    _id: Optional[str] = Field(None, alias="_id")
    expiredAt: Optional[str] = Field(None)
    createdAt: Optional[str] = Field(None)
