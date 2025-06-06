from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from app.db import Database
import app.utils as helpers
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"

class Account(BaseModel):
    """Account model for database operations"""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str = Field(default="Default Account", min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: str = Field(default="active", pattern=r'^(active|inactive|suspended)$')
    expiresAt: Optional[datetime] = None
    expiredAt: Optional[datetime] = None
    maxUsers: int = Field(default=10, ge=1, le=100)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(populate_by_name=True)

    _metadata: ClassVar[Dict[str, Any]] = {
        'entity': 'Account',
        'fields': {
            'name': {
                'type': 'String',
                'required': True,
                'min_length': 3,
                'max_length': 100
            },
            'description': {
                'type': 'String',
                'required': False,
                'max_length': 500
            },
            'status': {
                'type': 'String',
                'required': True,
                'enum': {
                    'values': ['active', 'inactive', 'suspended'],
                    'message': 'must be active, inactive, or suspended'
                }
            },
            'expiresAt': {
                'type': 'ISODate',
                'required': False
            },
            'maxUsers': {
                'type': 'Integer',
                'required': True,
                'ge': 1,
                'le': 100,
                'ui': {'displayName': 'Maximum Users'}
            },
            'expiredAt': {
                'type': 'ISODate',
                'required': False
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
                    'displayAfterField': 'createdAt',
                    'displayPages': 'details'
                }
            }
        },
        'operations': 'crud',
        'ui': {
            'title': 'Accounts',
            'buttonLabel': 'Manage Accounts',
            'description': 'Manage Account Settings'
        }
    }

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)
 
    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await Database.find_all("account", cls)
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
            account = await Database.get_by_id("account", str(id), cls)
            if not account:
                raise NotFoundError("Account", id)
            return account
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Account", "get")

    async def save(self) -> Self:
        try:
            self.updatedAt = datetime.now(timezone.utc)
            data = self.model_dump(exclude={"id"})
            result = await Database.save_document("account", self.id, data)
            if not self.id and result and isinstance(result, dict) and result.get("_id"):
                self.id = result["_id"]
            return self
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
            result = await Database.delete_document("account", self.id)
            if not result:
                raise NotFoundError("Account", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Account", "delete")

class AccountCreate(BaseModel):
    """Model for creating a new account"""
    name: str = Field(default="Default Account", min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: str = Field(default="active", pattern=r'^(active|inactive|suspended)$')
    maxUsers: int = Field(default=10, ge=1, le=100)
    expiresAt: Optional[datetime] = None
    expiredAt: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)

class AccountUpdate(BaseModel):
    """Model for updating an existing account"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = Field(None, pattern=r'^(active|inactive|suspended)$')
    expiresAt: Optional[datetime] = None
    maxUsers: Optional[int] = Field(None, ge=1, le=100)

    model_config = ConfigDict(populate_by_name=True)

class AccountRead(BaseModel):
    """Model for reading account data"""
    id: str = Field(alias="_id")
    name: str = Field(min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    status: str = Field(pattern=r'^(active|inactive|suspended)$')
    expiresAt: Optional[datetime] = None
    expiredAt: Optional[datetime] = None
    maxUsers: int = Field(ge=1, le=100)
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
