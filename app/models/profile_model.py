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


class Profile(BaseModel):
    id: str | None = Field(default=None)
    name: str = Field(..., max_length=100)
    preferences: str | None = Field(default=None)
    radiusMiles: int | None = Field(default=None, ge=0)
    userId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'name': {   'type': 'String',
                              'required': True,
                              'max_length': 100},
                  'preferences': {   'type': 'String',
                                     'required': False,
                                     'ui': {'displayPages': 'details'}},
                  'radiusMiles': {   'type': 'Integer',
                                     'required': False,
                                     'ge': 0},
                  'userId': {   'type': 'ObjectId',
                                'ui': {   'show': {   'displayInfo': [   {   'displayPages': 'summary',
                                                                             'fields': [   'email']},
                                                                         {   'displayPages': 'create|edit',
                                                                             'fields': [   'email',
                                                                                           'username']}]}},
                                'required': True},
                  'createdAt': {   'type': 'Date',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'Datetime',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}}},
    'operations': '',
    'ui': {   'title': 'Profile',
              'buttonLabel': 'Manage User Profiles',
              'description': 'Manage User Preferences'},
    'services': [],
    'uniques': [['name', 'userId']]}

    class Settings:
        name = "profile"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Profile")


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
        response = await DatabaseFactory.get_all("Profile", sort, filter, page, pageSize)
        
        if response["data"]:
            for user_dict in response["data"]:
                # Process Pydantic and FK validation if enabled
                if validation:
                    utils.validate_model(cls, user_dict, "Profile")
                    await utils.validate_fks("Profile", user_dict, cls._metadata)
                
                # Populate view data if requested
                if view_spec:
                    await utils.populate_view(user_dict, view_spec, "Profile")
        
        return response


    @classmethod
    async def get(cls, id: str, view_spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        validation = Config.validation(False)
        
        response = await DatabaseFactory.get_by_id(str(id), "Profile")
        if response["data"]:
            user_dict = response["data"]
            
            # Process Pydantic and FK validation if enabled
            if validation:
                utils.validate_model(cls, user_dict, "Profile")
                await utils.validate_fks("Profile", user_dict, cls._metadata)
            
            # Populate view data if requested
            if view_spec:
                await utils.populate_view(user_dict, view_spec, "Profile")
        
        return response


    async def save(self, entity_id: str = '', validate: bool = True) -> tuple[Self, List[str]]:
        self.updatedAt = datetime.now(timezone.utc)

        data = self.model_dump(mode='python')

        if validate:
            # Pydantic validation
            validated_instance = utils.validate_model(self.__class__, data, "Profile")
            data = validated_instance.model_dump(mode='python')
            
            # FK validation (sends notifications, doesn't throw)
            await utils.validate_fks("Profile", data, self._metadata)
        
        # Unique validation (always enforced)
        unique_constraints = self._metadata.get('uniques', [])
        if unique_constraints:
            await utils.validate_uniques("Profile", data, unique_constraints, entity_id if entity_id.strip() else None)

        # Save document
        response = await DatabaseFactory.save("Profile", data, entity_id)
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
    async def delete(cls, profile_id: str) -> bool:
        return await DatabaseFactory.delete("Profile", profile_id)

class ProfileCreate(BaseModel):
    name: str = Field(..., max_length=100)
    preferences: str | None = Field(default=None)
    radiusMiles: int | None = Field(default=None, ge=0)
    userId: str = Field(...)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    preferences: str | None = Field(default=None)
    radiusMiles: int | None = Field(default=None, ge=0)
    userId: str | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
