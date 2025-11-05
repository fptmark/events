from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.core.metadata import MetadataService


class CrawlCreate(BaseModel):
    id: str | None = Field(default=None)
    lastParsedDate: datetime | None = Field(default=None)
    parseStatus: Dict[str, Any] | None = Field(default=None)
    errorsEncountered: List[str] | None = Field(default=None)
    urlId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    urlId: str = Field(...)
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


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
                  'urlId': {'type': 'ObjectId', 'required': True},
                  'createdAt': {   'type': 'Date',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True},
                                   'autoGenerate': True},
                  'updatedAt': {   'type': 'Datetime',
                                   'ui': {   'displayAfterField': '-1',
                                             'readOnly': True,
                                             'clientEdit': True},
                                   'autoUpdate': True}},
    'ui': {   'title': 'Crawls',
              'buttonLabel': 'Manage Crawls',
              'description': 'Manage Crawls of Event sites'},
    'services': {},
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
                      view_spec: Dict[str, Any],
                      filter_matching: str = "contains") -> Tuple[List[Dict[str, Any]], int]:
        "Get paginated, sorted, and filtered list of entity." 
        
        db = DatabaseFactory.get_instance()
        return await db.documents.get_all("Crawl", sort, filter, page, pageSize, view_spec, filter_matching)
        
    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any], top_level: bool = True) -> Tuple[Dict[str, Any], int, Optional[BaseException]]:
        db = DatabaseFactory.get_instance()
        return await db.documents.get("Crawl", id, view_spec, top_level)

    @classmethod
    async def create(cls, data: CrawlCreate, validate: bool = True) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.create("Crawl", data.model_dump())

    @classmethod
    async def update(cls, id, data: CrawlUpdate) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.update("Crawl", id, data.model_dump())

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        db = DatabaseFactory.get_instance()
        return await db.documents.delete("Crawl", id)
