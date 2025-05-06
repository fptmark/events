from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from beanie import PydanticObjectId
from elasticsearch import NotFoundError
import re
from db import Database
import app.utils as helpers

class EventBaseModel(BaseModel):
    __index__ = "event"
    __unique__ = []
    __mappings__ = {   'cost': {'type': 'double'},
    'createdAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'dateTime': {'format': 'strict_date_optional_time', 'type': 'date'},
    'location': {   'fields': {   'keyword': {   'ignore_above': 256,
                                                 'type': 'keyword'}},
                    'type': 'text'},
    'numOfExpectedAttendees': {'type': 'integer'},
    'recurrence': {   'fields': {   'keyword': {   'ignore_above': 256,
                                                   'type': 'keyword'}},
                      'type': 'text'},
    'tags': {'type': 'keyword'},
    'title': {   'fields': {   'keyword': {   'ignore_above': 256,
                                              'type': 'keyword'}},
                 'type': 'text'},
    'updatedAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'url': {   'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
               'type': 'text'}}

    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

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

class Event(EventBaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
 
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Event',
    'fields': {   'cost': {   'ge': 0,
                              'required': False,
                              'type': 'Number',
                              'ui': {'displayPages': 'details'}},
                  'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'dateTime': {'required': True, 'type': 'ISODate'},
                  'location': {   'max_length': 200,
                                  'required': False,
                                  'type': 'String'},
                  'numOfExpectedAttendees': {   'ge': 0,
                                                'required': False,
                                                'type': 'Integer',
                                                'ui': {   'displayPages': 'details'}},
                  'recurrence': {   'enum': {   'values': [   'daily',
                                                              'weekly',
                                                              'monthly',
                                                              'yearly']},
                                    'required': False,
                                    'type': 'String',
                                    'ui': {'displayPages': 'details'}},
                  'tags': {   'required': False,
                              'type': 'Array[String]',
                              'ui': {'displayPages': 'details'}},
                  'title': {   'max_length': 200,
                               'required': True,
                               'type': 'String'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'url': {   'pattern': {   'message': 'Bad URL format',
                                            'regex': '^https?://[^s]+$'},
                             'required': True,
                             'type': 'String'}},
    'operations': '',
    'ui': {'buttonLabel': 'Manage Events', 'title': 'Events'}}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)
 
    @classmethod
    def _from_es_hit(cls, hit: dict) -> "Event":
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

class EventCreate(BaseModel):
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'^https?://[^s]+$', v):
            raise ValueError('Bad URL format')
        return v
     
    @field_validator('title', mode='before')
    def validate_title(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('title must be at most 200 characters')
        return v
     
    @field_validator('dateTime', mode='before')
    def parse_dateTime(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    @field_validator('location', mode='before')
    def validate_location(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('location must be at most 200 characters')
        return v
     
    @field_validator('cost', mode='before')
    def validate_cost(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('cost must be at least 0')
        return v
     
    @field_validator('numOfExpectedAttendees', mode='before')
    def validate_numOfExpectedAttendees(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('numOfExpectedAttendees must be at least 0')
        return v
     
    @field_validator('recurrence', mode='before')
    def validate_recurrence(cls, v):
        _custom = {}
        allowed = ['daily', 'weekly', 'monthly', 'yearly']
        if v is not None and v not in allowed:
            raise ValueError('recurrence must be one of ' + ','.join(allowed))
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class EventUpdate(BaseModel):
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'^https?://[^s]+$', v):
            raise ValueError('Bad URL format')
        return v
     
    @field_validator('title', mode='before')
    def validate_title(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('title must be at most 200 characters')
        return v
     
    @field_validator('dateTime', mode='before')
    def parse_dateTime(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    @field_validator('location', mode='before')
    def validate_location(cls, v):
        _custom = {}
        if v is not None and len(v) > 200:
            raise ValueError('location must be at most 200 characters')
        return v
     
    @field_validator('cost', mode='before')
    def validate_cost(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('cost must be at least 0')
        return v
     
    @field_validator('numOfExpectedAttendees', mode='before')
    def validate_numOfExpectedAttendees(cls, v):
        _custom = {}
        if v is not None and v < 0:
            raise ValueError('numOfExpectedAttendees must be at least 0')
        return v
     
    @field_validator('recurrence', mode='before')
    def validate_recurrence(cls, v):
        _custom = {}
        allowed = ['daily', 'weekly', 'monthly', 'yearly']
        if v is not None and v not in allowed:
            raise ValueError('recurrence must be one of ' + ','.join(allowed))
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class EventRead(BaseModel):
    id: str = Field(alias="_id")
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
