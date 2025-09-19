from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.config import Config
from app.services.metadata import MetadataService
import app.models.utils as utils

class RecurrenceEnum(str, Enum):
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
 

class Event(BaseModel):
    id: str | None = Field(default=None)
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: str | None = Field(default=None, max_length=200)
    cost: float | None = Field(default=None, ge=0)
    numOfExpectedAttendees: int | None = Field(default=None, ge=0)
    recurrence: RecurrenceEnum | None = Field(default=None)
    tags: List[str] | None = Field(default=None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'url': {   'type': 'String',
                             'required': True,
                             'pattern': {   'regex': '^https?://[^s]+$',
                                            'message': 'Bad URL format'}},
                  'title': {   'type': 'String',
                               'required': True,
                               'max_length': 200},
                  'dateTime': {'type': 'Date', 'required': True},
                  'location': {   'type': 'String',
                                  'required': False,
                                  'max_length': 200},
                  'cost': {   'type': 'Number',
                              'required': False,
                              'ge': 0,
                              'ui': {'displayPages': 'details'}},
                  'numOfExpectedAttendees': {   'type': 'Integer',
                                                'required': False,
                                                'ge': 0,
                                                'ui': {   'displayPages': 'details'}},
                  'recurrence': {   'type': 'String',
                                    'required': False,
                                    'enum': {   'values': [   'daily',
                                                              'weekly',
                                                              'monthly',
                                                              'yearly']},
                                    'ui': {'displayPages': 'details'}},
                  'tags': {   'type': 'Array[String]',
                              'required': False,
                              'ui': {'displayPages': 'details'}},
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
    'ui': {'title': 'Events', 'buttonLabel': 'Manage Events'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "event"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Event")


    @classmethod
    async def get_all(cls,
                      sort: List[Tuple[str, str]], 
                      filter: Optional[Dict[str, Any]], 
                      page: int, 
                      pageSize: int, 
                      view_spec: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        "Get paginated, sorted, and filtered list of entity." 
        validate = Config.validation(True)
        
        # Get filtered data from database - RequestContext provides the parameters
        data_records, total_count = await DatabaseFactory.get_all("Event", sort, filter, page, pageSize)
        
        #if data_records:
        for data in data_records:
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, data, "Event")
            
            if validate:
                unique_constraints = cls._metadata.get('uniques', [])
                await utils.validate_uniques("Event", data, unique_constraints, None)
            
            # Populate view data if requested and validate fks
            await utils.process_fks("Event", data, validate, view_spec)
        
        return data_records, total_count

    @classmethod
    async def get(cls, id: str, view_spec: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        validate = Config.validation(False)
        
        data, record_count = await DatabaseFactory.get("Event", id)
        if data:
            
            # Always run Pydantic validation (required fields, types, ranges)
            utils.validate_model(cls, data, "Event")
            
            if validate:
                unique_constraints = cls._metadata.get('uniques', [])
                await utils.validate_uniques("Event", data, unique_constraints, None)
            
            # Populate view data if requested and validate fks
            await utils.process_fks("Event", data, validate, view_spec)
        
        return data, record_count


    @classmethod
    async def create(cls, data: Dict[str, Any], validate: bool = True) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)
        
        if validate:
            validated_instance = utils.validate_model(cls, data, "Event")
            data = validated_instance.model_dump(mode='python')
            
            unique_constraints = cls._metadata.get('uniques', [])
            await utils.validate_uniques("Event", data, unique_constraints, None)

            # Validate fks
            await utils.process_fks("Event", data, True)
        
        # Create new document
        return await DatabaseFactory.create("Event", data)

    @classmethod
    async def update(cls, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        data['updatedAt'] = datetime.now(timezone.utc)

        validated_instance = utils.validate_model(cls, data, "Event")
        data = validated_instance.model_dump(mode='python')
        
        unique_constraints = cls._metadata.get('uniques', [])
        await utils.validate_uniques("Event", data, unique_constraints, data['id'])

        # Validate fks
        await utils.process_fks("Event", data, True)
    
        # Update existing document
        return await DatabaseFactory.update("Event", data)

    @classmethod
    async def delete(cls, id: str) -> Tuple[Dict[str, Any], int]:
        return await DatabaseFactory.delete("Event", id)

class EventCreate(BaseModel):
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: str | None = Field(default=None, max_length=200)
    cost: float | None = Field(default=None, ge=0)
    numOfExpectedAttendees: int | None = Field(default=None, ge=0)
    recurrence: RecurrenceEnum | None = Field(default=None)
    tags: List[str] | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class EventUpdate(BaseModel):
    url: str | None = Field(default=None, pattern=r"^https?://[^s]+$")
    title: str | None = Field(default=None, max_length=200)
    dateTime: datetime | None = Field(default=None)
    location: str | None = Field(default=None, max_length=200)
    cost: float | None = Field(default=None, ge=0)
    numOfExpectedAttendees: int | None = Field(default=None, ge=0)
    recurrence: RecurrenceEnum | None = Field(default=None)
    tags: List[str] | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
