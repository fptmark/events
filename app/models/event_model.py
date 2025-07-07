from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Union, Annotated, Literal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from pydantic_core import core_schema
from typing_extensions import Annotated
import logging
from app.db import DatabaseFactory
import app.utils as helpers
from app.config import Config
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError
from app.notification import notify_validation_error, NotificationType, start_notifications, end_notifications, NotificationLevel, NotificationType

class RecurrenceEnum(str, Enum):
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
 

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query

    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class Event(BaseModel):
    id: str
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

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'id': {'type': 'ObjectId', 'autoGenerate': True},
                  'url': {   'type': 'String',
                             'required': True,
                             'pattern': {   'regex': '^https?://[^s]+$',
                                            'message': 'Bad URL format'}},
                  'title': {   'type': 'String',
                               'required': True,
                               'max_length': 200},
                  'dateTime': {'type': 'ISODate', 'required': True},
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
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
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
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def get_all(cls) -> Dict[str, Any]:
        try:
            # Start notification collection
            notifications = start_notifications("Event", "get_all")

            get_validations, unique_validations = Config.validations(True)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_docs, warnings, total_count = await DatabaseFactory.get_all("event", unique_constraints)
            
            events = []
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                for doc in raw_docs:
                    try:
                        events.append(cls.model_validate(doc))
                    except PydanticValidationError as e:
                        # Convert Pydantic errors to notifications
                        for error in e.errors():
                           notifications.add(
                                message=error['msg'],
                                level=NotificationLevel.WARNING,
                                type=NotificationType.VALIDATION,
                                entity="Event",
                                field_name=str(error['loc'][-1]),
                                value=error.get('input'),
                                entity_id=doc.get('id')
                            )

                        # Create instance without validation for failed docs
                        events.append(cls.model_construct(**doc))
            else:
                events = [cls.model_construct(**doc) for doc in raw_docs]  # NO validation  
            
            # Add database warnings
            for warning in warnings:
                notifications.add(
                    message=warning,
                    level=NotificationLevel.WARNING,
                    type=NotificationType.DATABASE,
                    entity="Event"
                )
            
            # Convert models to dictionaries for FastAPI response validation
            event_data = [event.model_dump() for event in events]
            
            # End notification collection and return entity-grouped response
            collection = end_notifications()
            return collection.to_entity_grouped_response(data=event_data, is_bulk=True)

        except Exception as e:
            raise DatabaseError(str(e), "Event", "get_all")


    @classmethod
    async def get(cls, id: str) -> tuple[Self, List[str]]:
        try:
            get_validations, unique_validations = Config.validations(False)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_doc, warnings = await DatabaseFactory.get_by_id("event", str(id), unique_constraints)
            if not raw_doc:
                raise NotFoundError("Event", id)
            
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
                            entity="Event",
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
            raise DatabaseError(str(e), "Event", "get")

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
                        entity="Event",
                        field=str(err["loc"][-1]),
                        value=err.get("input"),
                        operation="save"
                    )
                failures = [ValidationFailure(field=str(err["loc"][-1]), message=err["msg"], value=err.get("input")) for err in e.errors()]
                raise ValidationError(message="Validation failed before save", entity="Event", invalid_fields=failures)
            
            # Save document with unique constraints - pass complete data
            result, warnings = await DatabaseFactory.save_document("event", data, unique_constraints)

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
            raise DatabaseError(str(e), "Event", "save")
 
    @classmethod
    async def delete(cls, event_id: str) -> tuple[bool, List[str]]:
        if not event_id:
            raise ValidationError(
                message="Cannot delete event without ID",
                entity="Event",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("event", event_id)
            if not result:
                raise NotFoundError("Event", event_id)
            return True, []
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Event", "delete")

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
