from beanie import Document
from pydantic import Field
from typing import Optional, List, Dict
from datetime import datetime

class URL(Document):
    _id: Optional[str] = Field(None, alias="_id")
    url: Optional[str] = Field(None)
    params: Optional[Dict] = Field(None)
    updatedAt: Optional[str] = Field(None)
