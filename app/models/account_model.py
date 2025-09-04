from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.config import Config
from app.services.metadata import MetadataService
import app.models.utils as utils


class Account(BaseModel):
    id: str | None = Field(default=None)
    expiredAt: datetime | None = Field(default=None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'expiredAt': {'type': 'Date', 'required': False},
                  'createdAt': {   'type': 'Date',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'Datetime',
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

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Account")


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
        data_records, total_count = await DatabaseFactory.get_all("Account", sort, filter, page, pageSize)
        
        #if data_records:
        for data in data_records:
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, data, "Account")
            
            # Run FK validation if enabled by config
            if validation:
                await utils.validate_fks("Account", data, cls._metadata)
                
                # Run unique validation if enabled by config
                unique_constraints = cls._metadata.get('uniques', [])
                if unique_constraints:
                    await utils.validate_uniques("Account", data, unique_constraints, None)
            
            # Populate view data if requested
            if view_spec:
                    await utils.populate_view(data, view_spec, "Account")
        
        return data_records, total_count

    @classmethod
    async def get(cls, id: str, view_spec: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
        validation = Config.validation(False)
        
        data, record_count = await DatabaseFactory.get_by_id(str(id), "Account")
        if data:
            
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, data, "Account")
            
            # Run FK validation if enabled by config
            if validation:
                await utils.validate_fks("Account", data, cls._metadata)
                
                # Run unique validation if enabled by config
                unique_constraints = cls._metadata.get('uniques', [])
                if unique_constraints:
                    await utils.validate_uniques("Account", data, unique_constraints, None)
            
            # Populate view data if requested
            if view_spec:
                await utils.populate_view(data, view_spec, "Account")
        
        return data, record_count


    @classmethod
    async def create(cls, data: Dict[str, Any], validate: bool = True) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)
        
        if validate:
            # 1. Pydantic validation (missing fields + constraints)
            validated_instance = utils.validate_model(cls, data, "Account")
            data = validated_instance.model_dump(mode='python')
            
            # 2. FK validation
            await utils.validate_fks("Account", data, cls._metadata)
            
            # 3. Unique validation
            unique_constraints = cls._metadata.get('uniques', [])
            if unique_constraints:
                await utils.validate_uniques("Account", data, unique_constraints, None)

        # Create new document
        return await DatabaseFactory.create("Account", data)

    @classmethod
    async def update(cls, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)

        # Always validate for updates
        # 1. Pydantic validation (missing fields + constraints)
        validated_instance = utils.validate_model(cls, data, "Account")
        data = validated_instance.model_dump(mode='python')
        
        # 2. FK validation
        await utils.validate_fks("Account", data, cls._metadata)
        
        # 3. Unique validation
        unique_constraints = cls._metadata.get('uniques', [])
        if unique_constraints:
            await utils.validate_uniques("Account", data, unique_constraints, data['id'])

        # Update existing document
        return await DatabaseFactory.update("Account", data)

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.delete("Account", id)

class AccountCreate(BaseModel):
    expiredAt: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class AccountUpdate(BaseModel):
    expiredAt: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
