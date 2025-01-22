from beanie import Document
from pydantic import Field
from typing import Optional, List, Dict
from datetime import datetime

class TagAffinity(Document):
    _id: Optional[str] = Field(None, alias="_id")
    profileId: Optional[str] = Field(None)
    tag: Optional[str] = Field(None)
    affinity: Optional[int] = Field(None)
    updatedAt: Optional[str] = Field(None)
