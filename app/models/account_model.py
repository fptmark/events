from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError
import re
import logging
from app.db import DatabaseFactory
import app.utils as helpers
from app.config import Config
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError
from app.notification import notify_validation_error, NotificationType


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

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

    @field_validator('expiredAt', mode='before')
    def parse_expiredAt(cls, v):
        # Always validate - this will only be called when using model_validate()
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def get_all(cls) -> tuple[Sequence[Self], List[ValidationError]]:
        try:
            get_validations, unique_validations = Config.validations(True)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_docs, warnings = await DatabaseFactory.get_all("account", unique_constraints)
            
            accounts = []
            validation_errors = []
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                for doc in raw_docs:
                    try:
                        accounts.append(cls.model_validate(doc))
                    except PydanticValidationError as e:
                        # Convert Pydantic errors to notifications
                        for error in e.errors():
                            notify_validation_error(
                                message=f"Validation failed for field '{error['loc'][-1]}': {error['msg']}",
                                entity="Account",
                                field=str(error['loc'][-1]),
                                value=error.get('input')
                            )
                            validation_errors.append(ValidationError(
                                message=f"Validation failed for field '{error['loc'][-1]}': {error['msg']}",
                                entity="Account",
                                invalid_fields=[ValidationFailure(
                                    field=str(error['loc'][-1]),
                                    message=error['msg'],
                                    value=error.get('input')
                                )]
                            ))
                        # Create instance without validation for failed docs
                        accounts.append(cls(**doc))
            else:
                accounts = [cls(**doc) for doc in raw_docs]  # NO validation
            
            # Add database warnings to validation errors
            validation_errors.extend([ValidationError(message=w, entity="Account", invalid_fields=[]) for w in warnings])
            return accounts, validation_errors
        except Exception as e:
            raise DatabaseError(str(e), "Account", "get_all")


    @classmethod
    async def get(cls, id: str) -> Self:
        try:
            get_validations, unique_validations = Config.validations(False)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_doc, warnings = await DatabaseFactory.get_by_id("account", str(id), unique_constraints)
            if not raw_doc:
                raise NotFoundError("Account", id)
            
            # Database warnings are now handled by DatabaseFactory
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                try:
                    return cls.model_validate(raw_doc)  # WITH validation
                except PydanticValidationError as e:
                    # Convert validation errors to notifications
                    for error in e.errors():
                        notify_validation_error(
                            message=f"Validation failed for field '{error['loc'][-1]}': {error['msg']}",
                            entity="Account",
                            field=str(error['loc'][-1]),
                            value=error.get('input'),
                            operation="get"
                        )
                    return cls(**raw_doc)  # Fallback to no validation
            else:
                return cls(**raw_doc)  # NO validation
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Account", "get")

    async def save(self, doc_id: Optional[str] = None) -> Self:
        try:
            get_validations, unique_validations = Config.validations(True)
            unique_constraints = self._metadata.get('uniques', []) if unique_validations else []
            
            self.updatedAt = datetime.now(timezone.utc)
            if doc_id:
                self.id = doc_id

            # VALIDATE the instance BEFORE saving to prevent bad data in DB
            try:
                # This validates all fields and raises PydanticValidationError if invalid
                validated_instance = self.__class__.model_validate(self.model_dump())
                # Use the validated data for save
                data = validated_instance.model_dump(exclude={"id"})
            except PydanticValidationError as e:
                # Convert to notifications and ValidationError format
                for err in e.errors():
                    notify_validation_error(
                        message=f"Validation failed for field '{err['loc'][-1]}': {err['msg']}",
                        entity="Account",
                        field=str(err["loc"][-1]),
                        value=err.get("input"),
                        operation="save"
                    )
                failures = [ValidationFailure(field=str(err["loc"][-1]), message=err["msg"], value=err.get("input")) for err in e.errors()]
                raise ValidationError(message="Validation failed before save", entity="Account", invalid_fields=failures)
            
            # Save document with unique constraints
            doc_id_to_save = self.id or ""  # Use empty string if None, database will generate ID
            result, warnings = await DatabaseFactory.save_document("account", doc_id_to_save, data, unique_constraints)
            
            # Database warnings are now handled by DatabaseFactory
            
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

class AccountCreate(BaseModel):
  expiredAt: Optional[datetime] = Field(None)

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

class AccountUpdate(BaseModel):
  expiredAt: Optional[datetime] = Field(None)

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

