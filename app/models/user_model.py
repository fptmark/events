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


class User(BaseModel):
    id: Optional[str] = Field(default=None, alias='_id')
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    netWorth: Optional[float] = Field(None, ge=0, le=10000000)
    accountId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'id': {'type': 'ObjectId', 'autoGenerate': True},
                  'username': {   'type': 'String',
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

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to normalize ID field to 'id' for API responses"""
        data = super().model_dump(**kwargs)
        # Normalize database-specific _id to generic id
        if "_id" in data:
            data["id"] = data.pop("_id")
        return data

    @field_validator('username', mode='before')
    def validate_username(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if v is not None and len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v
     
    @field_validator('email', mode='before')
    def validate_email(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if v is not None and len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v
     
    @field_validator('password', mode='before')
    def validate_password(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v
     
    @field_validator('firstName', mode='before')
    def validate_firstName(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v
     
    @field_validator('lastName', mode='before')
    def validate_lastName(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v
     
    @field_validator('gender', mode='before')
    def validate_gender(cls, v):
        allowed = ['male', 'female', 'other']
        if v is not None and v not in allowed:
            raise ValueError('must be male or female')
        return v
     
    @field_validator('dob', mode='before')
    def parse_dob(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v
    @field_validator('netWorth', mode='before')
    def validate_netWorth(cls, v):
        parsed = v
        if v is None: return None
        parsed = helpers.parse_currency(v)
        if parsed is None:
            raise ValueError('netWorth must be a valid currency')
        if parsed < 0:
            raise ValueError('netWorth must be at least 0')
        if parsed > 10000000:
            raise ValueError('netWorth must be at most 10000000')
        return parsed

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def get_all(cls) -> tuple[Sequence[Self], List[ValidationError]]:
        try:
            get_validations, unique_validations = Config.validations(True)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_docs, warnings = await DatabaseFactory.get_all("user", unique_constraints)
            
            users = []
            validation_errors = []
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                for doc in raw_docs:
                    try:
                        users.append(cls.model_validate(doc))
                    except PydanticValidationError as e:
                        # Convert Pydantic errors to notifications
                        for error in e.errors():
                            notify_validation_error(
                                message=f"Validation failed for field '{error['loc'][-1]}': {error['msg']}",
                                entity="User",
                                field=str(error['loc'][-1]),
                                value=error.get('input')
                            )
                            validation_errors.append(ValidationError(
                                message=f"Validation failed for field '{error['loc'][-1]}': {error['msg']}",
                                entity="User",
                                invalid_fields=[ValidationFailure(
                                    field=str(error['loc'][-1]),
                                    message=error['msg'],
                                    value=error.get('input')
                                )]
                            ))
                        # Create instance without validation for failed docs
                        users.append(cls(**doc))
            else:
                users = [cls(**doc) for doc in raw_docs]  # NO validation
            
            # Add database warnings to validation errors
            validation_errors.extend([ValidationError(message=w, entity="User", invalid_fields=[]) for w in warnings])
            return users, validation_errors
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
                    for error in e.errors():
                        notify_validation_error(
                            message=f"Validation failed for field '{error['loc'][-1]}': {error['msg']}",
                            entity="User",
                            field=str(error['loc'][-1]),
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
                for err in e.errors():
                    notify_validation_error(
                        message=f"Validation failed for field '{err['loc'][-1]}': {err['msg']}",
                        entity="User",
                        field=str(err["loc"][-1]),
                        value=err.get("input"),
                        operation="save"
                    )
                failures = [ValidationFailure(field=str(err["loc"][-1]), message=err["msg"], value=err.get("input")) for err in e.errors()]
                raise ValidationError(message="Validation failed before save", entity="User", invalid_fields=failures)
            
            # Save document with unique constraints - pass complete data
            result, warnings = await DatabaseFactory.save_document("user", data, unique_constraints)

            # Update ID from result
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

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

#from pydantic import BaseModel, Field, ConfigDict
#from typing import Optional, List, Dict, Any
#from datetime import datetime

class UserCreate(BaseModel):
  id: Optional[str] = Field(default=None, alias='_id')
  username: str = Field(..., min_length=3, max_length=50)
  email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
  password: str = Field(..., min_length=8)
  firstName: str = Field(..., min_length=3, max_length=100)
  lastName: str = Field(..., min_length=3, max_length=100)
  gender: Optional[str] = Field(None, description ="must be male or female")
  dob: Optional[datetime] = Field(None)
  isAccountOwner: bool = Field(...)
  netWorth: Optional[float] = Field(None, ge=0, le=10000000)
  accountId: str = Field(...)

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)


#from pydantic import BaseModel, Field, ConfigDict
#from typing import Optional, List, Dict, Any
#from datetime import datetime

class UserUpdate(BaseModel):
  id: Optional[str] = Field(default=None, alias='_id')
  username: str = Field(..., min_length=3, max_length=50)
  email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
  password: str = Field(..., min_length=8)
  firstName: str = Field(..., min_length=3, max_length=100)
  lastName: str = Field(..., min_length=3, max_length=100)
  gender: Optional[str] = Field(None, description ="must be male or female")
  dob: Optional[datetime] = Field(None)
  isAccountOwner: bool = Field(...)
  netWorth: Optional[float] = Field(None, ge=0, le=10000000)
  accountId: str = Field(...)

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

