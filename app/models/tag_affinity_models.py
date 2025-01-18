from pydantic import BaseModel, Field

class TagAffinity(BaseModel):
    id: str = Field(..., alias="_id")
    profileId: str
    tag: str
    affinity: int  # Positive = Like, Negative = Dislike
