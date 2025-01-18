from pydantic import BaseModel, Field
from datetime import datetime

class Crawl(BaseModel):
    id: str = Field(..., alias="_id")
    urlId: str
    lastParsedDate: datetime
    parseStatus: dict
    errorsEncountered: list[str]
