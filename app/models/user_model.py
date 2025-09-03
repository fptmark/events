from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.config import Config
from app.services.notification import validation_warning, Notification
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
                # Always run Pydantic validation (required fields, types, ranges)
                utils.validate_model(cls, user_dict, "User")
                
                # Run FK validation if enabled by config
                if validation:
                    await utils.validate_fks("User", user_dict, cls._metadata)
                    
                    # Run unique validation if enabled by config
                    unique_constraints = cls._metadata.get('uniques', [])
                    if unique_constraints:
                        await utils.validate_uniques("User", user_dict, unique_constraints, None)
                
                # Populate view data if requested
                if view_spec:
                    await utils.populate_view(user_dict, view_spec, "User")
        
        return utils.build_standard_response(response)


    @classmethod
    async def get(cls, id: str, view_spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        validation = Config.validation(False)
        
        response = await DatabaseFactory.get_by_id(str(id), "User")
        if response["data"]:
            user_dict = response["data"]
            
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, user_dict, "User")
            
            # Run FK validation if enabled by config
            if validation:
                await utils.validate_fks("User", user_dict, cls._metadata)
                
                # Run unique validation if enabled by config
                unique_constraints = cls._metadata.get('uniques', [])
                if unique_constraints:
                    await utils.validate_uniques("User", user_dict, unique_constraints, None)
            
            # Populate view data if requested
            if view_spec:
                await utils.populate_view(user_dict, view_spec, "User")
        
        return utils.build_standard_response(response)


    @classmethod
    async def create(cls, data: Dict[str, Any], validate: bool = True) -> Dict[str, Any]:
        # Set updatedAt timestamp
        data['updatedAt'] = datetime.now(timezone.utc)
        
        if validate:
            # 1. Pydantic validation (missing fields + constraints)
            validated_instance = utils.validate_model(cls, data, "User")
            data = validated_instance.model_dump(mode='python')
            
            # 2. FK validation
            await utils.validate_fks("User", data, cls._metadata)
            
            # 3. Unique validation
            unique_constraints = cls._metadata.get('uniques', [])
            if unique_constraints:
                await utils.validate_uniques("User", data, unique_constraints, None)

        # Create new document
        response = await DatabaseFactory.create("User", data)
        # result = response["data"]

        return utils.build_standard_response(response)

    @classmethod
    async def update(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        if 'id' not in data or not data['id']:
            validation_warning(message="Missing 'id' field or value for update operation", 
                               entity="User", 
                               field="id")
            return  utils.build_error_response("warning")
            
        # Set updatedAt timestamp
        data['updatedAt'] = datetime.now(timezone.utc)
        
        # Always validate for updates
        # 1. Pydantic validation (missing fields + constraints)
        validated_instance = utils.validate_model(cls, data, "User")
        data = validated_instance.model_dump(mode='python')
        # 2. FK validation
        await utils.validate_fks("User", data, cls._metadata)
        
        # 3. Unique validation
        unique_constraints = cls._metadata.get('uniques', [])
        if unique_constraints:
            await utils.validate_uniques("User", data, unique_constraints, data['id'])

        # Update existing document
        response = await DatabaseFactory.update("User", data)
        # result = response["data"]
        # success = response.get("success", False)

        return utils.build_standard_response(response)

 
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
