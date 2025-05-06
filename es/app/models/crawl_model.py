from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from beanie import PydanticObjectId
from elasticsearch import NotFoundError
import re
from db import Database
import app.utils as helpers

class CrawlBaseModel(BaseModel):
    __index__ = "crawl"
    __unique__ = []
    __mappings__ = {   'createdAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'errorsEncountered': {'type': 'keyword'},
    'lastParsedDate': {'format': 'strict_date_optional_time', 'type': 'date'},
    'parseStatus': {'enabled': False, 'type': 'object'},
    'updatedAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'urlId': {'type': 'keyword'}}

    model_config = ConfigDict(populate_by_name=True)

    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)

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

class Crawl(CrawlBaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
 
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Crawl',
    'fields': {   'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'errorsEncountered': {   'required': False,
                                           'type': 'Array[String]'},
                  'lastParsedDate': {'required': False, 'type': 'ISODate'},
                  'parseStatus': {'required': False, 'type': 'JSON'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'urlId': {   'displayName': 'urlId',
                               'readOnly': True,
                               'required': True,
                               'type': 'ObjectId'}},
    'operations': 'rd',
    'ui': {   'buttonLabel': 'Manage Crawls',
              'description': 'Manage Crawls of Event sites',
              'title': 'Crawls'}}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)
 
    @classmethod
    def _from_es_hit(cls, hit: dict) -> "Crawl":
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

class CrawlCreate(BaseModel):
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)

    @field_validator('lastParsedDate', mode='before')
    def parse_lastParsedDate(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class CrawlUpdate(BaseModel):
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)

    @field_validator('lastParsedDate', mode='before')
    def parse_lastParsedDate(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class CrawlRead(BaseModel):
    id: str = Field(alias="_id")
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: PydanticObjectId = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
