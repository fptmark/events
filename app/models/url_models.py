from pydantic import BaseModel, Field

class URL(BaseModel):
    id: str = Field(..., alias="_id")
    url: str
    params: dict
