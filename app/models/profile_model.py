from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict

class Profile(Document):
    _id: Optional[str] = Field(None, alias="_id")
    userId: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    preferences: Optional[Dict] = Field(None)
    radiusMiles: Optional[int] = Field(None)
    createdAt: Optional[str] = Field(None)
    updatedAt: Optional[str] = Field(None)
