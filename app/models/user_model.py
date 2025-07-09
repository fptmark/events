from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Union, Annotated, Literal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from pydantic_core import core_schema
from typing_extensions import Annotated
import logging
import warnings as python_warnings
from app.db import DatabaseFactory
import app.utils as helpers
from app.config import Config
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError
from app.notification import notify_validation_error, notify_warning, NotificationType

logger = logging.getLogger(__name__)

class GenderEnum(str, Enum):
    MALE = 'male'
    FEMALE = 'female'
    OTHER = 'other'
 

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query

    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class User(BaseModel):
    id: str | None = Field(default=None)
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: GenderEnum | None = Field(default=None)
    dob: datetime | None = Field(default=None)
    isAccountOwner: bool = Field(...)
    netWorth: float | None = Field(default=None, ge=0, le=10000000)
    accountId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'username': {   'type': 'String',
                                  'required': True,
                                  'min_length': 3,
                                  'max_length': 50},
                  'email': {   'type': 'String',
                               'required': True,
                               'min_length': 8,
                               'max_length': 50,
                               'pattern': {   'regex': '^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$',
                                              'message': 'Bad email address '
                                                         'format'}},
                  'password': {   'type': 'String',
                                  'required': True,
                                  'min_length': 8,
                                  'ui': {   'displayPages': 'details',
                                            'display': 'secret'}},
                  'firstName': {   'type': 'String',
                                   'required': True,
                                   'min_length': 3,
                                   'max_length': 100,
                                   'ui': {'displayName': 'First Name'}},
                  'lastName': {   'type': 'String',
                                  'required': True,
                                  'min_length': 3,
                                  'max_length': 100,
                                  'ui': {'displayName': 'Last Name'}},
                  'gender': {   'type': 'String',
                                'required': False,
                                'enum': {   'values': [   'male',
                                                          'female',
                                                          'other'],
                                            'message': 'must be male or '
                                                       'female'}},
                  'dob': {'type': 'ISODate', 'required': False},
                  'isAccountOwner': {   'type': 'Boolean',
                                        'required': True,
                                        'ui': {'displayName': 'Owner'}},
                  'netWorth': {'type': 'Currency', 'ge': 0, 'le': 10000000},
                  'accountId': {   'type': 'ObjectId',
                                   'ui': {   'displayName': 'Account',
                                             'show': {   'endpoint': 'account',
                                                         'displayInfo': [   {   'displayPages': 'summary',
                                                                                'fields': [   'createdAt']},
                                                                            {   'displayPages': 'edit|create',
                                                                                'fields': [   'createdAt',
                                                                                              'expiredAt']}]}},
                                   'required': True},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1',
                                             'displayPages': 'summary'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}}},
    'operations': 'rcu',
    'ui': {   'title': 'Users',
              'buttonLabel': 'Manage Users',
              'description': 'Manage User Profile'},
    'services': ['auth.cookies.redis'],
    'uniques': [['username'], ['email']]}

    class Settings:
        name = "user"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def get_all(cls) -> Dict[str, Any]:
        try:
            get_validations, unique_validations = Config.validations(True)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_docs, warnings, total_count = await DatabaseFactory.get_all("user", unique_constraints)
            
            users = []
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                for doc in raw_docs:
                    try:
                        users.append(cls.model_validate(doc))
                    except PydanticValidationError as e:
                        # Convert Pydantic errors to notifications
                        entity_id = doc.get('id')
                        if not entity_id:
                            logger.error(f"User document missing ID field: {doc}")
                            notify_warning("Document missing ID field", NotificationType.DATABASE)
                            entity_id = "missing"
  
                        for error in e.errors():
                            field_name = str(error['loc'][-1])
                            notify_validation_error(
                                message=f"User {entity_id}.{field_name}:  validation failed - {error['msg']}",
                                entity="User",
                                field=field_name,
                                value=error.get('input'),
                                operation="get_all"
                            )

                        # Create instance without validation for failed docs
                        users.append(cls.model_construct(**doc))
            else:
                users = [cls.model_construct(**doc) for doc in raw_docs]  # NO validation  
            
            # Add database warnings
            for warning in warnings:
                notify_warning(warning, NotificationType.DATABASE)
            
            # Convert models to dictionaries for FastAPI response validation
            user_data = []
            for user in users:
                with python_warnings.catch_warnings(record=True) as caught_warnings:
                    python_warnings.simplefilter("always")
                    data_dict = user.model_dump()
                    user_data.append(data_dict)
                    
                    # Add any serialization warnings as notifications
                    if caught_warnings:
                        entity_id = data_dict.get('id')
                        if not entity_id:
                            logger.error(f"User document missing ID field: {data_dict}")
                            notify_warning("Document missing ID field", NotificationType.DATABASE)
                            entity_id = "missing"

                        datetime_field_names = []
                        
                        # Use the model's metadata to find datetime fields
                        for field_name, field_meta in cls._metadata.get('fields', {}).items():
                            if field_meta.get('type') == 'ISODate':
                                if field_name in data_dict and isinstance(data_dict[field_name], str):
                                    datetime_field_names.append(field_name)
                        
                        if datetime_field_names:
                            field_list = ', '.join(datetime_field_names)
                            notify_warning(f"User {entity_id}: {field_list} datetime serialization warnings", NotificationType.VALIDATION)
                        else:
                            # Fallback for non-datetime warnings
                            warning_count = len(caught_warnings)
                            notify_warning(f"User {entity_id}: {warning_count} serialization warnings", NotificationType.VALIDATION)
 
            return {"data": user_data}
            
        except Exception as e:
            raise DatabaseError(str(e), "User", "get_all")


    @classmethod
    async def get(cls, id: str) -> tuple[Self, List[str]]:
        try:
            get_validations, unique_validations = Config.validations(False)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_doc, warnings = await DatabaseFactory.get_by_id("user", str(id), unique_constraints)
            if not raw_doc:
                raise NotFoundError("User", id)
            
            # Database warnings are now handled by DatabaseFactory
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                try:
                    return cls.model_validate(raw_doc), warnings  # WITH validation
                except PydanticValidationError as e:
                    # Convert validation errors to notifications
                    entity_id = raw_doc.get('id')
                    if not entity_id:
                        logger.error(f"User document missing ID field: {raw_doc}")
                        notify_warning("Document missing ID field", NotificationType.DATABASE)
                        entity_id = "missing"
                    for error in e.errors():
                        field_name = str(error['loc'][-1])
                        notify_validation_error(
                            message=f"User {entity_id}: {field_name} validation failed - {error['msg']}",
                            entity="User",
                            field=field_name,
                            value=error.get('input'),
                            operation="get"
                        )
                    return cls(**raw_doc), warnings  # Fallback to no validation
            else:
                return cls(**raw_doc), warnings  # NO validation
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "get")

    async def save(self) -> tuple[Self, List[str]]:
        try:
            _, unique_validations = Config.validations(True)
            unique_constraints = self._metadata.get('uniques', []) if unique_validations else []
            
            self.updatedAt = datetime.now(timezone.utc)
            
            # VALIDATE the instance BEFORE saving to prevent bad data in DB
            try:
                # This validates all fields and raises PydanticValidationError if invalid
                validated_instance = self.__class__.model_validate(self.model_dump())
                # Use the validated data for save
                data = validated_instance.model_dump()
            except PydanticValidationError as e:
                # Convert to notifications and ValidationError format
                entity_id = self.id
                if not entity_id:
                    logger.error(f"User instance missing ID during save: {self.model_dump()}")
                    notify_warning("User instance missing ID during save", NotificationType.DATABASE)
                    entity_id = "missing"

                for err in e.errors():
                    field_name = str(err["loc"][-1])
                    notify_validation_error(
                        message=f"User {entity_id}: {field_name} validation failed - {err['msg']}",
                        entity="User",
                        field=field_name,
                        value=err.get("input"),
                        operation="save"
                    )
                failures = [ValidationFailure(field=str(err["loc"][-1]), message=err["msg"], value=err.get("input")) for err in e.errors()]
                raise ValidationError(message="Validation failed before save", entity="User", invalid_fields=failures)
            
            # Save document with unique constraints - pass complete data
            result, warnings = await DatabaseFactory.save_document("user", data, unique_constraints)

            # Update ID from result
            if not self.id and result and isinstance(result, dict):
                extracted_id = result.get('id')
                if extracted_id:
                    self.id = extracted_id

            return self, warnings
        except ValidationError:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "save")
 
    @classmethod
    async def delete(cls, user_id: str) -> tuple[bool, List[str]]:
        if not user_id:
            raise ValidationError(
                message="Cannot delete user without ID",
                entity="User",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("user", user_id)
            if not result:
                raise NotFoundError("User", user_id)
            return True, []
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "delete")

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: GenderEnum | None = Field(default=None)
    dob: datetime | None = Field(default=None)
    isAccountOwner: bool = Field(...)
    netWorth: float | None = Field(default=None, ge=0, le=10000000)
    accountId: str = Field(...)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: str | None = Field(default=None, min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str | None = Field(default=None, min_length=8)
    firstName: str | None = Field(default=None, min_length=3, max_length=100)
    lastName: str | None = Field(default=None, min_length=3, max_length=100)
    gender: GenderEnum | None = Field(default=None)
    dob: datetime | None = Field(default=None)
    isAccountOwner: bool | None = Field(default=None)
    netWorth: float | None = Field(default=None, ge=0, le=10000000)
    accountId: str | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
