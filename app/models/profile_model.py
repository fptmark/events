from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.config import Config
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
                      view_spec: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        "Get paginated, sorted, and filtered list of entity." 
        validation = Config.validation(True)
        
        # Get filtered data from database - RequestContext provides the parameters
        data_records, total_count = await DatabaseFactory.get_all("Profile", sort, filter, page, pageSize)
        
        #if data_records:
        for data in data_records:
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, data, "Profile")
            
            # Run FK validation if enabled by config
            if validation:
                await utils.validate_fks("Profile", data, cls._metadata)
                
                # Run unique validation if enabled by config
                unique_constraints = cls._metadata.get('uniques', [])
                if unique_constraints:
                    await utils.validate_uniques("Profile", data, unique_constraints, None)
            
            # Populate view data if requested
            if view_spec:
                    await utils.populate_view(data, view_spec, "Profile")
        
        return data_records, total_count

    @classmethod
    async def get(cls, id: str, view_spec: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
        validation = Config.validation(False)
        
        data, record_count = await DatabaseFactory.get_by_id(str(id), "Profile")
        if data:
            
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, data, "Profile")
            
            # Run FK validation if enabled by config
            if validation:
                await utils.validate_fks("Profile", data, cls._metadata)
                
                # Run unique validation if enabled by config
                unique_constraints = cls._metadata.get('uniques', [])
                if unique_constraints:
                    await utils.validate_uniques("Profile", data, unique_constraints, None)
            
            # Populate view data if requested
            if view_spec:
                await utils.populate_view(data, view_spec, "Profile")
        
        return data, record_count


    @classmethod
    async def create(cls, data: Dict[str, Any], validate: bool = True) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)
        
        if validate:
            # 1. Pydantic validation (missing fields + constraints)
            validated_instance = utils.validate_model(cls, data, "Profile")
            data = validated_instance.model_dump(mode='python')
            
            # 2. FK validation
            await utils.validate_fks("Profile", data, cls._metadata)
            
            # 3. Unique validation
            unique_constraints = cls._metadata.get('uniques', [])
            if unique_constraints:
                await utils.validate_uniques("Profile", data, unique_constraints, None)

        # Create new document
        return await DatabaseFactory.create("Profile", data)

    @classmethod
    async def update(cls, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)

        # Always validate for updates
        # 1. Pydantic validation (missing fields + constraints)
        validated_instance = utils.validate_model(cls, data, "Profile")
        data = validated_instance.model_dump(mode='python')
        
        # 2. FK validation
        await utils.validate_fks("Profile", data, cls._metadata)
        
        # 3. Unique validation
        unique_constraints = cls._metadata.get('uniques', [])
        if unique_constraints:
            await utils.validate_uniques("Profile", data, unique_constraints, data['id'])

        # Update existing document
        return await DatabaseFactory.update("Profile", data)

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.delete("Profile", id)

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
