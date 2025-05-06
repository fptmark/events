from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from beanie import PydanticObjectId
from elasticsearch import NotFoundError
import re
from db import Database
import app.utils as helpers

class UserEventBaseModel(BaseModel):
    __index__ = "userevent"
    __unique__ = []
    __mappings__ = {   'attended': {'type': 'boolean'},
    'createdAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'eventId': {'type': 'keyword'},
    'note': {   'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
                'type': 'text'},
    'rating': {'type': 'integer'},
    'updatedAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'userId': {'type': 'keyword'}}

    model_config = ConfigDict(populate_by_name=True)

    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def _id(self) -> Optional[str]:
        return self.id
    @_id.setter
    def _id(self, value: Optional[str]) -> None:
        self.id = value
    async def save(self):
        # get the Elasticsearch client
        es = Database.get_es_client()
        if not es:
            raise RuntimeError("Elasticsearch client not initialized — did you forget to call Database.init()?")
     
        # save any autoupdate fields
        self.updatedAt = datetime.now(timezone.utc)
        # serialize & index
        body = self.model_dump(by_alias=True, exclude={"id"})
        resp = await es.index(
            index=self.__index__,
            id=self.id,
            document=body,
            refresh="wait_for",
        )
        self.id = resp["_id"]
        return self

class UserEvent(UserEventBaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
 
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'UserEvent',
    'fields': {   'attended': {'required': False, 'type': 'Boolean'},
                  'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'eventId': {   'displayName': 'eventId',
                                 'readOnly': True,
                                 'required': True,
                                 'type': 'ObjectId'},
                  'note': {   'max_length': 500,
                              'required': False,
                              'type': 'String',
                              'ui': {'displayPages': 'details'}},
                  'rating': {   'ge': 1,
                                'le': 5,
                                'required': False,
                                'type': 'Integer'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'userId': {   'displayName': 'userId',
                                'readOnly': True,
                                'required': True,
                                'type': 'ObjectId'}},
    'operations': '',
    'ui': {'buttonLabel': 'Manage Event Attendance', 'title': 'User Events'}}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)
 
    @classmethod
    def _from_es_hit(cls, hit: dict) -> "UserEvent":
        data = hit["_source"]
        data["id"] = hit["_id"]
        return cls(**data)

    @classmethod
    async def get(cls, item_id: str):
        es = Database.get_es_client()
        if not es:
            raise RuntimeError("Elasticsearch client not initialized — did you forget to call Database.init()?")
        try:
            result = await es.get(index=cls.__index__, id=item_id)
            return cls._from_es_hit(result.body)
        except Exception:
            return None

    @classmethod
    async def find_all(cls) -> List[Self]:
        es = Database.get_es_client()
        if not es:
            raise RuntimeError("Elasticsearch client not initialized — did you forget to call Database.init()?")
        try:
            result = await es.search(index=cls.__index__, query={"match_all": {}}, size=1000)
            return [cls._from_es_hit(hit) for hit in result["hits"]["hits"]] #type: ignore[return-value]
        except NotFoundError:
            return []  # Return empty list if index doesn't exist

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserEventCreate(BaseModel):
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)

    @field_validator('rating', mode='before')
    def validate_rating(cls, v):
        _custom = {}
        if v is not None and v < 1:
            raise ValueError('rating must be at least 1')
        if v is not None and v > 5:
            raise ValueError('rating must be at most 5')
        return v
     
    @field_validator('note', mode='before')
    def validate_note(cls, v):
        _custom = {}
        if v is not None and len(v) > 500:
            raise ValueError('note must be at most 500 characters')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserEventUpdate(BaseModel):
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)

    @field_validator('rating', mode='before')
    def validate_rating(cls, v):
        _custom = {}
        if v is not None and v < 1:
            raise ValueError('rating must be at least 1')
        if v is not None and v > 5:
            raise ValueError('rating must be at most 5')
        return v
     
    @field_validator('note', mode='before')
    def validate_note(cls, v):
        _custom = {}
        if v is not None and len(v) > 500:
            raise ValueError('note must be at most 500 characters')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserEventRead(BaseModel):
    id: str = Field(alias="_id")
    attended: Optional[bool] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = Field(None, max_length=500)
    userId: PydanticObjectId = Field(...)
    eventId: PydanticObjectId = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
