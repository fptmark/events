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


class Account(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    expiredAt: Optional[datetime] = Field(None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'expiredAt': {'type': 'ISODate', 'required': False},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': 'createdAt',
                                             'displayPages': 'details'}}},
    'operations': '',
    'ui': {'title': 'Accounts', 'buttonLabel': 'Manage Accounts'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "account"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('expiredAt', mode='before')
    def parse_expiredAt(cls, v):
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
            return await DatabaseFactory.find_all("account", cls)
        except Exception as e:
            raise DatabaseError(str(e), "Account", "find_all")

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
            account = await DatabaseFactory.get_by_id("account", str(id), cls)
            if not account:
                raise NotFoundError("Account", id)
            return account
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Account", "get")

    async def save(self, doc_id: Optional[str] = None) -> Self:
        try:
            self.updatedAt = datetime.now(timezone.utc)
            if doc_id:
                self.id = doc_id

            data = self.model_dump(exclude={"id"})
            
            # Get unique constraints from metadata
            unique_constraints = self._metadata.get('uniques', [])
            
            # Save document with unique constraints
            result = await DatabaseFactory.save_document("account", self.id, data, unique_constraints)
            
            # Update ID from result
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

            return self
        except ValidationError:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Account", "save")
            
    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete account without ID",
                entity="Account",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("account", self.id)
            if not result:
                raise NotFoundError("Account", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Account", "delete")

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class AccountCreate(BaseModel):
  expiredAt: Optional[datetime] = Field(None)

  @field_validator('expiredAt', mode='before')
  def parse_expiredAt(cls, v):
      if v in (None, '', 'null'):
          return None
      if isinstance(v, str):
          return datetime.fromisoformat(v)
      return v

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)


from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class AccountUpdate(BaseModel):
  expiredAt: Optional[datetime] = Field(None)

  @field_validator('expiredAt', mode='before')
  def parse_expiredAt(cls, v):
      if v in (None, '', 'null'):
          return None
      if isinstance(v, str):
          return datetime.fromisoformat(v)
      return v

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

