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


class Url(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    url: str = Field(..., pattern=r"main.url")
    params: Optional[Dict[str, Any]] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'url': {   'type': 'String',
                             'required': True,
                             'pattern': {   'regex': 'main.url',
                                            'message': 'Bad URL format'}},
                  'params': {'type': 'JSON', 'required': False},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}}},
    'operations': '',
    'ui': {   'title': 'Url',
              'buttonLabel': 'Manage Urls',
              'description': 'Manage Event Urls'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "url"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('url', mode='before')
    def validate_url(cls, v):
        if v is not None and not re.match(r'main.url', v):
            raise ValueError('Bad URL format')
        return v
     

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def find_all(cls) -> tuple[Sequence[Self], List[ValidationError]]:
        try:
            return await DatabaseFactory.find_all("url", cls)
        except Exception as e:
            raise DatabaseError(str(e), "Url", "find_all")

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
            url = await DatabaseFactory.get_by_id("url", str(id), cls)
            if not url:
                raise NotFoundError("Url", id)
            return url
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Url", "get")

    async def save(self, doc_id: Optional[str] = None) -> Self:
        try:
            self.updatedAt = datetime.now(timezone.utc)
            if doc_id:
                self.id = doc_id

            data = self.model_dump(exclude={"id"})
            
            # Get unique constraints from metadata
            unique_constraints = self._metadata.get('uniques', [])
            
            # Save document with unique constraints
            result = await DatabaseFactory.save_document("url", self.id, data, unique_constraints)
            
            # Update ID from result
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

            return self
        except ValidationError:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Url", "save")
            
    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete url without ID",
                entity="Url",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("url", self.id)
            if not result:
                raise NotFoundError("Url", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Url", "delete")

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UrlCreate(BaseModel):
  url: str = Field(..., pattern=r"main.url")
  params: Optional[Dict[str, Any]] = Field(None)

  @field_validator('url', mode='before')
  def validate_url(cls, v):
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
      if v is not None and not re.match(r'main.url', v):
          raise ValueError('Bad URL format')
      return v
   

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

