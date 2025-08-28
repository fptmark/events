from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.config import Config
from app.services.notification import validation_warning
from app.services.request_context import RequestContext
from app.services.metadata import MetadataService
import app.models.utils as utils

class GenderEnum(str, Enum):
    MALE = 'male'
    FEMALE = 'female'
    OTHER = 'other'
 


class User(BaseModel):
    id: str | None = Field(default=None)
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9](.?[a-zA-Z0-9_+%-])*@[a-zA-Z0-9-]+(.[a-zA-Z0-9-]+)*.[a-zA-Z]{2,}$")
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

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'username': {   'type': 'String',
                                  'required': True,
                                  'min_length': 3,
                                  'max_length': 50},
                  'email': {   'type': 'String',
                               'required': True,
                               'min_length': 8,
                               'max_length': 50,
                               'pattern': {   'regex': '^[a-zA-Z0-9](.?[a-zA-Z0-9_+%-])*@[a-zA-Z0-9-]+(.[a-zA-Z0-9-]+)*.[a-zA-Z]{2,}$',
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
                  'dob': {'type': 'Date', 'required': False},
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
                  'createdAt': {   'type': 'Date',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1',
                                             'displayPages': 'summary'}},
                  'updatedAt': {   'type': 'Datetime',
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
        return MetadataService.get("User")


    @classmethod
    async def get_all(cls) -> Dict[str, Any]:
        """Get paginated, sorted, and filtered list of entity."""
        validation = Config.validation(True)
        
        # Get filtered data from database - RequestContext provides the parameters
        response = await DatabaseFactory.get_all()
        
        if response["data"] and validation:
            for user_dict in response["data"]:
                fk_success = await utils.process_entity_fks(user_dict, None, "User", cls, validation)
                # For get operations, continue regardless of FK validation results
        
        return response


    @classmethod
    async def get(cls, id: str) -> Dict[str, Any]:
        validation = Config.validation(False)
        
        response = await DatabaseFactory.get_by_id(str(id))
        if response["data"] and (RequestContext.view_spec or validation):
            fk_success = await utils.process_entity_fks(response["data"], RequestContext.view_spec, "User", cls, validation)
                # For get operations, continue regardless of FK validation results
            
        return response

    async def save(self, entity_id: str = '', validate: bool = True) -> tuple[Self, List[str]]:
        self.updatedAt = datetime.now(timezone.utc)

        if validate:
            # VALIDATE the instance BEFORE saving to prevent bad data in DB
            try:
                # This validates all fields and raises PydanticValidationError if invalid
                validated_instance = self.__class__.model_validate(self.model_dump())
                # Use the validated data for save
                data = validated_instance.model_dump(mode='python')
                                
                # Validate ObjectId references exist
                await utils.validate_objectid_references("User", data, MetadataService.get("User"))
            except PydanticValidationError as e:
                # Convert to notifications
                for error in e.errors():
                    field_name = str(error["loc"][-1])
                    validation_warning(
                        message=error['msg'],
                        entity="User",
                        entity_id=entity_id or "new",
                        field=field_name
                    )
                # Return failure with empty warnings list since warnings are in notification system
                return self, []
        else:
            data = self.model_dump(mode='python')

        # Save document - RequestContext provides entity context
        response = await DatabaseFactory.save(data, entity_id)
        result = response["data"]
        warnings = response.get("warnings", [])

        # Check if save was successful based on response content
        if not result:
            # Save failed - warnings already in notification system
            return self, warnings

        # Update ID from result
        if not self.id and result and isinstance(result, dict):
            extracted_id = result.get('id')
            if extracted_id:
                self.id = extracted_id

        return self, warnings
 
    @classmethod
    async def delete(cls, user_id: str) -> tuple[bool, List[str]]:
        result = await DatabaseFactory.delete(user_id)
        # Database layer handles not found warnings automatically
        return result, []

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9](.?[a-zA-Z0-9_+%-])*@[a-zA-Z0-9-]+(.[a-zA-Z0-9-]+)*.[a-zA-Z]{2,}$")
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
    email: str | None = Field(default=None, min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9](.?[a-zA-Z0-9_+%-])*@[a-zA-Z0-9-]+(.[a-zA-Z0-9-]+)*.[a-zA-Z]{2,}$")
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
