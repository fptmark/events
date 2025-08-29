from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
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
    async def get_all(cls,
                      sort: List[Tuple[str, str]], 
                      filter: Optional[Dict[str, Any]], 
                      page: int, 
                      pageSize: int, 
                      view_spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        "Get paginated, sorted, and filtered list of entity." 
        validation = Config.validation(True)
        
        # Get filtered data from database - RequestContext provides the parameters
        response = await DatabaseFactory.get_all("User", sort, filter, page, pageSize)
        
        if response["data"]:
            for user_dict in response["data"]:
                # Process Pydantic and FK validation if enabled
                if validation:
                    utils.validate_model(cls, user_dict, "User")
                    await utils.validate_fks("User", user_dict, cls._metadata)
                
                # Populate view data if requested
                if view_spec:
                    await utils.populate_view(user_dict, view_spec, "User")
        
        return response


    @classmethod
    async def get(cls, id: str, view_spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        validation = Config.validation(False)
        
        response = await DatabaseFactory.get_by_id(str(id), "User")
        if response["data"]:
            user_dict = response["data"]
            
            # Process Pydantic and FK validation if enabled
            if validation:
                utils.validate_model(cls, user_dict, "User")
                await utils.validate_fks("User", user_dict, cls._metadata)
            
            # Populate view data if requested
            if view_spec:
                await utils.populate_view(user_dict, view_spec, "User")
        
        return response


    async def save(self, entity_id: str = '', validate: bool = True) -> tuple[Self, List[str]]:
        self.updatedAt = datetime.now(timezone.utc)

        data = self.model_dump(mode='python')

        if validate:
            # Pydantic validation
            validated_instance = utils.validate_model(self.__class__, data, "User")
            data = validated_instance.model_dump(mode='python')
            
            # FK validation (sends notifications, doesn't throw)
            await utils.validate_fks("User", data, self._metadata)
        
        # Unique validation (always enforced)
        unique_constraints = self._metadata.get('uniques', [])
        if unique_constraints:
            await utils.validate_uniques("User", data, unique_constraints, entity_id if entity_id.strip() else None)

        # Save document
        response = await DatabaseFactory.save("User", data, entity_id)
        result = response["data"]
        warnings = response.get("warnings", [])

        # Check if save was successful based on response content
        if not result:
            return self, warnings

        # Update ID from result
        if not self.id and result and isinstance(result, dict):
            extracted_id = result.get('id')
            if extracted_id:
                self.id = extracted_id

        return self, warnings

 
    @classmethod
    async def delete(cls, user_id: str) -> bool:
        return await DatabaseFactory.delete("User", user_id)

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
