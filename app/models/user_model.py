from beanie import Document
from pydantic import Field
from typing import Optional, List, Dict
from datetime import datetime

class User(Document):
    _id: Optional[str] = Field(None, alias="_id")
    accountId: Optional[str] = Field(None)
    username: Optional[str] = Field(None)
    password: Optional[str] = Field(None)
    name: Optional[str] = Field(None)
    isAccountOwner: Optional[bool] = Field(None)
    createdAt: Optional[str] = Field(None)
    updatedAt: Optional[str] = Field(None)
