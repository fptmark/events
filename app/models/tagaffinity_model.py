from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.config import Config
from app.services.metadata import MetadataService
import app.models.utils as utils


class TagAffinity(BaseModel):
    id: str | None = Field(default=None)
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'tag': {'type': 'String', 'required': True, 'max_length': 50},
                  'affinity': {   'type': 'Integer',
                                  'required': True,
                                  'ge': -100,
                                  'le': 100},
                  'createdAt': {   'type': 'Date',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'Datetime',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}},
                  'profileId': {'type': 'ObjectId', 'required': True}},
    'operations': '',
    'ui': {'title': 'Tag Affinity', 'buttonLabel': 'Manage Event Affinity'},
    'services': [],
    'uniques': [['profileId', 'tag']]}

    class Settings:
        name = "tagaffinity"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("TagAffinity")


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
        data_records, total_count = await DatabaseFactory.get_all("TagAffinity", sort, filter, page, pageSize)
        
        #if data_records:
        for data in data_records:
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, data, "TagAffinity")
            
            # Run FK validation if enabled by config
            if validation:
                await utils.validate_fks("TagAffinity", data, cls._metadata)
                
                # Run unique validation if enabled by config
                unique_constraints = cls._metadata.get('uniques', [])
                if unique_constraints:
                    await utils.validate_uniques("TagAffinity", data, unique_constraints, None)
            
            # Populate view data if requested
            if view_spec:
                    await utils.populate_view(data, view_spec, "TagAffinity")
        
        return data_records, total_count

    @classmethod
    async def get(cls, id: str, view_spec: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
        validation = Config.validation(False)
        
        data, record_count = await DatabaseFactory.get_by_id(str(id), "TagAffinity")
        if data:
            
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, data, "TagAffinity")
            
            # Run FK validation if enabled by config
            if validation:
                await utils.validate_fks("TagAffinity", data, cls._metadata)
                
                # Run unique validation if enabled by config
                unique_constraints = cls._metadata.get('uniques', [])
                if unique_constraints:
                    await utils.validate_uniques("TagAffinity", data, unique_constraints, None)
            
            # Populate view data if requested
            if view_spec:
                await utils.populate_view(data, view_spec, "TagAffinity")
        
        return data, record_count


    @classmethod
    async def create(cls, data: Dict[str, Any], validate: bool = True) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)
        
        if validate:
            # 1. Pydantic validation (missing fields + constraints)
            validated_instance = utils.validate_model(cls, data, "TagAffinity")
            data = validated_instance.model_dump(mode='python')
            
            # 2. FK validation
            await utils.validate_fks("TagAffinity", data, cls._metadata)
            
            # 3. Unique validation
            unique_constraints = cls._metadata.get('uniques', [])
            if unique_constraints:
                await utils.validate_uniques("TagAffinity", data, unique_constraints, None)

        # Create new document
        return await DatabaseFactory.create("TagAffinity", data)

    @classmethod
    async def update(cls, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)

        # Always validate for updates
        # 1. Pydantic validation (missing fields + constraints)
        validated_instance = utils.validate_model(cls, data, "TagAffinity")
        data = validated_instance.model_dump(mode='python')
        
        # 2. FK validation
        await utils.validate_fks("TagAffinity", data, cls._metadata)
        
        # 3. Unique validation
        unique_constraints = cls._metadata.get('uniques', [])
        if unique_constraints:
            await utils.validate_uniques("TagAffinity", data, unique_constraints, data['id'])

        # Update existing document
        return await DatabaseFactory.update("TagAffinity", data)

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.delete("TagAffinity", id)

class TagAffinityCreate(BaseModel):
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class TagAffinityUpdate(BaseModel):
    tag: str | None = Field(default=None, max_length=50)
    affinity: int | None = Field(default=None, ge=-100, le=100)
    profileId: str | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
