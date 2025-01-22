from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict

class User(Document):
    _id: Optional[str] = Field(None, alias="_id")
    accountId: Optional[str] = Field(None)
    username: Optional[str] = Field(None)
    password: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    isAccountOwner: Optional[bool] = Field(None)
    createdAt: Optional[str] = Field(None)
    updatedAt: Optional[str] = Field(None)
