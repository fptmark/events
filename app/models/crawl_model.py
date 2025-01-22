from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, List, Dict

class Crawl(Document):
    _id: Optional[str] = Field(None, alias="_id")
    url_id: Optional[str] = Field(None)
    last_parsed_date: Optional[str] = Field(None)
    parse_status: Optional[Dict] = Field(None)
    errors_encountered: Optional[List] = Field(None)
    updatedAt: Optional[str] = Field(None)
