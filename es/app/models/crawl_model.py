from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from elasticsearch import NotFoundError
import re
from app.db import Database
import app.utils as helpers

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class CrawlBase(BaseModel):
    """Base Crawl model with common fields and validation"""
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    frequency: str = Field(..., pattern=r'^(hourly|daily|weekly|monthly)$')
    lastCrawlTime: Optional[datetime] = None
    nextCrawlTime: Optional[datetime] = None
    status: str = Field(..., pattern=r'^(active|paused|error)$')
    errorMessage: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list)

    @field_validator('url')
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('url must start with http:// or https://')
        return v

    @field_validator('frequency')
    def validate_frequency(cls, v: str) -> str:
        allowed = ['hourly', 'daily', 'weekly', 'monthly']
        if v not in allowed:
            raise ValueError(f'frequency must be one of: {", ".join(allowed)}')
        return v

    @field_validator('lastCrawlTime')
    def parse_last_crawl_time(cls, v: Any) -> Optional[datetime]:
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError('lastCrawlTime must be in ISO format')
        return v

    @field_validator('nextCrawlTime')
    def parse_next_crawl_time(cls, v: Any) -> Optional[datetime]:
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError('nextCrawlTime must be in ISO format')
        return v

    @field_validator('status')
    def validate_status(cls, v: str) -> str:
        allowed = ['active', 'paused', 'error']
        if v not in allowed:
            raise ValueError(f'status must be one of: {", ".join(allowed)}')
        return v

    @field_validator('errorMessage')
    def validate_error_message(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 1000:
            raise ValueError('errorMessage must be at most 1000 characters')
        return v

    @field_validator('tags')
    def validate_tags(cls, v: List[str]) -> List[str]:
        if len(v) > 20:
            raise ValueError('maximum 20 tags allowed')
        for tag in v:
            if len(tag) > 50:
                raise ValueError('tag must be at most 50 characters')
        return v

class Crawl(CrawlBase):
    """Crawl model for database operations"""
    id: Optional[str] = Field(default=None, alias="_id")
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {
        'entity': 'Crawl',
        'fields': {
            'url': {
                'type': 'String',
                'required': True,
                'pattern': {
                    'regex': '^https?://[^s]+$',
                    'message': 'Bad URL format'
                }
            },
            'frequency': {
                'type': 'String',
                'required': True,
                'enum': {
                    'values': ['hourly', 'daily', 'weekly', 'monthly'],
                    'message': 'must be hourly, daily, weekly, or monthly'
                }
            },
            'lastCrawlTime': {
                'type': 'ISODate',
                'required': False,
                'ui': {'displayName': 'Last Crawl'}
            },
            'nextCrawlTime': {
                'type': 'ISODate',
                'required': False,
                'ui': {'displayName': 'Next Crawl'}
            },
            'status': {
                'type': 'String',
                'required': True,
                'enum': {
                    'values': ['active', 'paused', 'error'],
                    'message': 'must be active, paused, or error'
                }
            },
            'errorMessage': {
                'type': 'String',
                'required': False,
                'max_length': 1000,
                'ui': {
                    'multiline': True,
                    'rows': 3,
                    'displayName': 'Error Message'
                }
            },
            'tags': {
                'type': 'Array',
                'items': {
                    'type': 'String',
                    'max_length': 50
                },
                'max_items': 20
            },
            'lastParsedDate': {
                'type': 'ISODate',
                'required': False,
                'ui': {'displayName': 'Last Parsed Date'}
            },
            'parseStatus': {
                'type': 'JSON',
                'required': False,
                'ui': {'displayName': 'Parse Status'}
            },
            'errorsEncountered': {
                'type': 'Array[String]',
                'required': False,
                'ui': {'displayName': 'Errors Encountered'}
            },
            'createdAt': {
                'type': 'ISODate',
                'autoGenerate': True,
                'ui': {
                    'readOnly': True,
                    'displayAfterField': '-1'
                }
            },
            'updatedAt': {
                'type': 'ISODate',
                'autoUpdate': True,
                'ui': {
                    'readOnly': True,
                    'clientEdit': True,
                    'displayAfterField': '-1'
                }
            },
            'urlId': {
                'type': 'ObjectId',
                'required': True,
                'ui': {'displayName': 'URL ID'}
            }
        },
        'operations': 'crud',
        'ui': {
            'title': 'Crawls',
            'buttonLabel': 'Manage Crawls',
            'description': 'Manage Web Crawlers'
        }
    }

    class Settings:
        name = "crawl"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)
 
    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        return await Database.find_all("crawl", cls)

    # Method to imitate Beanie's find() method
    @classmethod
    def find(cls):
        # This is a simple adapter to keep the API compatible
        # It provides a to_list() method that calls find_all()
        class FindAdapter:
            @staticmethod
            async def to_list():
                return await cls.find_all()

        return FindAdapter()

    # Replaces Beanie's get - uses common Database function
    @classmethod
    async def get(cls, id) -> Optional[Self]:
        return await Database.get_by_id("crawl", str(id), cls)

    # Replaces Beanie's save - uses common Database function
    async def save(self, *args, **kwargs):
        # Update timestamp
        self.updatedAt = datetime.now(timezone.utc)

        # Convert model to dict
        data = self.model_dump(exclude={"id"})

        # Save document using common function
        result = await Database.save_document("crawl", self.id, data)

        # Update ID if this was a new document
        if not self.id and result and isinstance(result, dict) and result.get("_id"):
            self.id = result["_id"]

        return self

    # Replaces Beanie's delete - uses common Database function
    async def delete(self):
        if self.id:
            return await Database.delete_document("crawl", self.id)
        return False

class CrawlCreate(CrawlBase):
    """Model for creating a new crawl"""
    pass

class CrawlUpdate(CrawlBase):
    """Model for updating an existing crawl"""
    pass

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class CrawlRead(BaseModel):
    id: str = Field(alias="_id")
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: str = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
