from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from app.db import DatabaseFactory
import app.utils as helpers
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError


class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query

    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class Crawl(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    lastParsedDate: Optional[datetime] = Field(None)
    parseStatus: Optional[Dict[str, Any]] = Field(None)
    errorsEncountered: Optional[List[str]] = Field(None)
    urlId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'lastParsedDate': {'type': 'ISODate', 'required': False},
                  'parseStatus': {'type': 'JSON', 'required': False},
                  'errorsEncountered': {   'type': 'Array[String]',
                                           'required': False},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
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

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('lastParsedDate', mode='before')
    def parse_lastParsedDate(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await DatabaseFactory.find_all("crawl", cls)
        except Exception as e:
            raise DatabaseError(str(e), "Crawl", "find_all")

    @classmethod
    def find(cls):
        class FindAdapter:
            @staticmethod
            async def to_list():
                return await cls.find_all()

        return FindAdapter()

    @classmethod
    async def get(cls, id: str) -> Self:
        try:
            crawl = await DatabaseFactory.get_by_id("crawl", str(id), cls)
            if not crawl:
                raise NotFoundError("Crawl", id)
            return crawl
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Crawl", "get")

    async def save(self, doc_id: Optional[str] = None) -> Self:
        try:
            self.updatedAt = datetime.now(timezone.utc)
            if doc_id:
                self.id = doc_id

            data = self.model_dump(exclude={"id"})
            
            # Get unique constraints from metadata
            unique_constraints = self._metadata.get('uniques', [])
            
            # Save document with unique constraints
            result = await DatabaseFactory.save_document("crawl", self.id, data, unique_constraints)
            
            # Update ID from result
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

            return self
        except ValidationError:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Crawl", "save")
            
    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete crawl without ID",
                entity="Crawl",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("crawl", self.id)
            if not result:
                raise NotFoundError("Crawl", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Crawl", "delete")

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class CrawlCreate(BaseModel):
  lastParsedDate: Optional[datetime] = Field(None)
  parseStatus: Optional[Dict[str, Any]] = Field(None)
  errorsEncountered: Optional[List[str]] = Field(None)
  urlId: str = Field(...)

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
  urlId: str = Field(...)

  @field_validator('lastParsedDate', mode='before')
  def parse_lastParsedDate(cls, v):
      if v in (None, '', 'null'):
          return None
      if isinstance(v, str):
          return datetime.fromisoformat(v)
      return v

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

