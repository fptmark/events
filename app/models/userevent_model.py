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


class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query

    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class UserEvent(BaseModel):
    id: str
    attended: bool | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'id': {'type': 'ObjectId', 'autoGenerate': True},
                  'attended': {'type': 'Boolean', 'required': False},
                  'rating': {   'type': 'Integer',
                                'required': False,
                                'ge': 1,
                                'le': 5},
                  'note': {   'type': 'String',
                              'required': False,
                              'max_length': 500,
                              'ui': {'displayPages': 'details'}},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}},
                  'userId': {'type': 'ObjectId', 'required': True},
                  'eventId': {'type': 'ObjectId', 'required': True}},
    'operations': '',
    'ui': {'title': 'User Events', 'buttonLabel': 'Manage Event Attendance'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "userevent"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def get_all(cls) -> Dict[str, Any]:
        try:
            # Start notification collection
            notifications = start_notifications("UserEvent", "get_all")

            get_validations, unique_validations = Config.validations(True)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_docs, warnings, total_count = await DatabaseFactory.get_all("userevent", unique_constraints)
            
            userevents = []
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                for doc in raw_docs:
                    try:
                        userevents.append(cls.model_validate(doc))
                    except PydanticValidationError as e:
                        # Convert Pydantic errors to notifications
                        for error in e.errors():
                           notifications.add(
                                message=error['msg'],
                                level=NotificationLevel.WARNING,
                                type=NotificationType.VALIDATION,
                                entity="UserEvent",
                                field_name=str(error['loc'][-1]),
                                value=error.get('input'),
                                entity_id=doc.get('id')
                            )

                        # Create instance without validation for failed docs
                        userevents.append(cls.model_construct(**doc))
            else:
                userevents = [cls.model_construct(**doc) for doc in raw_docs]  # NO validation  
            
            # Add database warnings
            for warning in warnings:
                notifications.add(
                    message=warning,
                    level=NotificationLevel.WARNING,
                    type=NotificationType.DATABASE,
                    entity="UserEvent"
                )
            
            # Convert models to dictionaries for FastAPI response validation
            userevent_data = [userevent.model_dump() for userevent in userevents]
            
            # End notification collection and return entity-grouped response
            collection = end_notifications()
            return collection.to_entity_grouped_response(data=userevent_data, is_bulk=True)

        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "get_all")


    @classmethod
    async def get(cls, id: str) -> tuple[Self, List[str]]:
        try:
            get_validations, unique_validations = Config.validations(False)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_doc, warnings = await DatabaseFactory.get_by_id("userevent", str(id), unique_constraints)
            if not raw_doc:
                raise NotFoundError("UserEvent", id)
            
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
                            entity="UserEvent",
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
            raise DatabaseError(str(e), "UserEvent", "get")

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
                        entity="UserEvent",
                        field=str(err["loc"][-1]),
                        value=err.get("input"),
                        operation="save"
                    )
                failures = [ValidationFailure(field=str(err["loc"][-1]), message=err["msg"], value=err.get("input")) for err in e.errors()]
                raise ValidationError(message="Validation failed before save", entity="UserEvent", invalid_fields=failures)
            
            # Save document with unique constraints - pass complete data
            result, warnings = await DatabaseFactory.save_document("userevent", data, unique_constraints)

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
            raise DatabaseError(str(e), "UserEvent", "save")
 
    @classmethod
    async def delete(cls, userevent_id: str) -> tuple[bool, List[str]]:
        if not userevent_id:
            raise ValidationError(
                message="Cannot delete userevent without ID",
                entity="UserEvent",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("userevent", userevent_id)
            if not result:
                raise NotFoundError("UserEvent", userevent_id)
            return True, []
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "UserEvent", "delete")

class UserEventCreate(BaseModel):
    attended: bool | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=500)
    userId: str = Field(...)
    eventId: str = Field(...)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class UserEventUpdate(BaseModel):
    attended: bool | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    note: str | None = Field(default=None, max_length=500)
    userId: str | None = Field(default=None)
    eventId: str | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
