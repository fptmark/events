from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.services.metadata import MetadataService


class Crawl(BaseModel):
    id: str | None = Field(default=None)
    lastParsedDate: datetime | None = Field(default=None)
    parseStatus: Dict[str, Any] | None = Field(default=None)
    errorsEncountered: List[str] | None = Field(default=None)
    urlId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'lastParsedDate': {'type': 'Date', 'required': False},
                  'parseStatus': {'type': 'JSON', 'required': False},
                  'errorsEncountered': {   'type': 'Array[String]',
                                           'required': False},
                  'createdAt': {   'type': 'Date',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'Datetime',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}},
                  'urlId': {'type': 'ObjectId', 'required': True}},
    'operations': 'rd',
    'ui': {   'title': 'Crawls',
              'buttonLabel': 'Manage Crawls',
              'description': 'Manage Crawls of Event sites'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "crawl"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Crawl")

    @classmethod
    async def get_all(cls,
                      sort: List[Tuple[str, str]], 
                      filter: Optional[Dict[str, Any]], 
                      page: int, 
                      pageSize: int, 
                      view_spec: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        "Get paginated, sorted, and filtered list of entity." 
        
        return await DatabaseFactory.get_all("Crawl", sort, filter, page, pageSize, view_spec)
        
    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.get("Crawl", id)

    @classmethod
    async def create(cls, data: Dict[str, Any], validate: bool = True) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)
        return await DatabaseFactory.create("Crawl", data)

    @classmethod
    async def update(cls, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)
        return await DatabaseFactory.update("Crawl", data)

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.delete("Crawl", id)

class CrawlCreate(BaseModel):
    id: str | None = Field(default=None)
    lastParsedDate: datetime | None = Field(default=None)
    parseStatus: Dict[str, Any] | None = Field(default=None)
    errorsEncountered: List[str] | None = Field(default=None)
    urlId: str = Field(...)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class CrawlUpdate(BaseModel):
    id: str | None = Field(default=None)
    lastParsedDate: datetime | None = Field(default=None)
    parseStatus: Dict[str, Any] | None = Field(default=None)
    errorsEncountered: List[str] | None = Field(default=None)
    urlId: str | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
