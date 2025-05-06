from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from beanie import PydanticObjectId
from elasticsearch import NotFoundError
import re
from db import Database
import app.utils as helpers

class UrlBaseModel(BaseModel):
    __index__ = "url"
    __unique__ = []
    __mappings__ = {   'createdAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'params': {'enabled': False, 'type': 'object'},
    'updatedAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'url': {   'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
               'type': 'text'}}

    model_config = ConfigDict(populate_by_name=True)

    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

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

class Url(UrlBaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
 
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'Url',
    'fields': {   'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True}},
                  'params': {'required': False, 'type': 'JSON'},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'url': {   'pattern': {   'message': 'Bad URL format',
                                            'regex': 'main.url'},
                             'required': True,
                             'type': 'String'}},
    'operations': '',
    'ui': {   'buttonLabel': 'Manage Urls',
              'description': 'Manage Event Urls',
              'title': 'Url'}}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)
 
    @classmethod
    def _from_es_hit(cls, hit: dict) -> "Url":
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

class UrlCreate(BaseModel):
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UrlUpdate(BaseModel):
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        _custom = {}
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UrlRead(BaseModel):
    id: str = Field(alias="_id")
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
