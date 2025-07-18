from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Union, Annotated, Literal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from pydantic_core import core_schema
import warnings as python_warnings
from app.db import DatabaseFactory
import app.utils as helpers
from app.config import Config
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError
from app.notification import notify_warning, NotificationType


class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query

    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class Crawl(BaseModel):
    id: str | None = Field(default=None)
    lastParsedDate: datetime | None = Field(default=None)
    parseStatus: Dict[str, Any] | None = Field(default=None)
    errorsEncountered: List[str] | None = Field(default=None)
    urlId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() + 'Z' if v else None  # Always UTC with Z suffix
        }
    )

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'lastParsedDate': {'type': 'Date', 'required': False},
                  'parseStatus': {'type': 'JSON', 'required': False},
                  'errorsEncountered': {   'type': 'Array[String]',
                                           'required': False},
                  'createdAt': {   'type': 'Date',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'Datetime',
                                   'autoUpdate': True,
                                   'ui': {   'readOnly': True,
                                             'clientEdit': True,
                                             'displayAfterField': '-1'}},
                  'urlId': {'type': 'ObjectId', 'required': True}},
    'operations': 'rd',
    'ui': {   'title': 'Crawls',
              'buttonLabel': 'Manage Crawls',
              'description': 'Manage Crawls of Event sites'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "crawl"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata("Crawl", cls._metadata)

    @classmethod
    async def get_all(cls) -> Dict[str, Any]:
        try:
            get_validations, unique_validations = Config.validations(True)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_docs, warnings, total_count = await DatabaseFactory.get_all("crawl", unique_constraints)
            
            crawls = []
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                for doc in raw_docs:
                    try:
                        crawls.append(cls.model_validate(doc))
                    except PydanticValidationError as e:
                        # Convert Pydantic errors to notifications
                        entity_id = doc.get('id')
                        if not entity_id:
                            notify_warning("Document missing ID field", NotificationType.DATABASE, entity=Crawl)
                            entity_id = "missing"
  
                        for error in e.errors():
                            field_name = str(error['loc'][-1])
                            notify_warning(
                                message=error['msg'],
                                type=NotificationType.VALIDATION,
                                entity="Crawl",
                                field_name=field_name,
                                value=error.get('input'),
                                operation="get_all",
                                entity_id=entity_id
                            )

                        # Create instance without validation for failed docs
                        crawls.append(cls.model_construct(**doc))
            else:
                crawls = [cls.model_construct(**doc) for doc in raw_docs]  # NO validation  
            
            # Add database warnings
            for warning in warnings:
                notify_warning(warning, NotificationType.DATABASE)
            
            # Convert models to dictionaries for FastAPI response validation
            crawl_data = []
            for crawl in crawls:
                with python_warnings.catch_warnings(record=True) as caught_warnings:
                    python_warnings.simplefilter("always")
                    data_dict = crawl.model_dump()
                    crawl_data.append(data_dict)
                    
                    # Add any serialization warnings as notifications
                    if caught_warnings:
                        entity_id = data_dict.get('id')
                        if not entity_id:
                            notify_warning("Document missing ID field", NotificationType.DATABASE)
                            entity_id = "missing"

                        datetime_field_names = []
                        
                        # Use the model's metadata to find datetime fields
                        for field_name, field_meta in cls._metadata.get('fields', {}).items():
                            if field_meta.get('type') == 'ISODate':
                                if field_name in data_dict and isinstance(data_dict[field_name], str):
                                    datetime_field_names.append(field_name)
                        
                        if datetime_field_names:
                            field_list = ', '.join(datetime_field_names)
                            notify_warning(f"{field_list} datetime serialization warnings", NotificationType.VALIDATION, entity="Crawl", entity_id=entity_id)
                        else:
                            # Fallback for non-datetime warnings
                            warning_count = len(caught_warnings)
                            notify_warning(f"User {entity_id}: {warning_count} serialization warnings", NotificationType.VALIDATION, entity="Crawl")
 
            return {"data": crawl_data}
            
        except Exception as e:
            raise DatabaseError(str(e), "Crawl", "get_all")


    @classmethod
    async def get(cls, id: str) -> tuple[Self, List[str]]:
        try:
            get_validations, unique_validations = Config.validations(False)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_doc, warnings = await DatabaseFactory.get_by_id("crawl", str(id), unique_constraints)
            if not raw_doc:
                raise NotFoundError("Crawl", id)
            
            # Database warnings are now handled by DatabaseFactory
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                try:
                    return cls.model_validate(raw_doc), warnings  # WITH validation
                except PydanticValidationError as e:
                    # Convert validation errors to notifications
                    entity_id = raw_doc.get('id')
                    if not entity_id:
                        notify_warning("Document missing ID field", NotificationType.DATABASE)
                        entity_id = "missing"
                    for error in e.errors():
                        field_name = str(error['loc'][-1])
                        notify_warning(
                            message=f"Crawl {entity_id}: {field_name} validation failed - {error['msg']}",
                            type=NotificationType.VALIDATION,
                            entity="Crawl",
                            field_name=field_name,
                            value=error.get('input'),
                            operation="get",
                            entity_id=entity_id
                        )
                    return cls.model_construct(**raw_doc), warnings  # Fallback to no validation
            else:
                return cls.model_construct(**raw_doc), warnings  # NO validation
        except NotFoundError:
            raise
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Crawl", "get")

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
                entity_id = self.id
                if not entity_id:
                    notify_warning("User instance missing ID during save", NotificationType.DATABASE)
                    entity_id = "missing"

                for err in e.errors():
                    field_name = str(err["loc"][-1])
                    notify_warning(
                        message=f"Crawl {entity_id}: {field_name} validation failed - {err['msg']}",
                        type=NotificationType.VALIDATION,
                        entity="Crawl",
                        field_name=field_name,
                        value=err.get("input"),
                        operation="save"
                    )
                failures = [ValidationFailure(field_name=str(err["loc"][-1]), message=err["msg"], value=err.get("input")) for err in e.errors()]
                raise ValidationError(message="Validation failed before save", entity="Crawl", invalid_fields=failures)
            
            # Save document with unique constraints - pass complete data
            result, warnings = await DatabaseFactory.save_document("crawl", data, unique_constraints)

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
            raise DatabaseError(str(e), "Crawl", "save")
 
    @classmethod
    async def delete(cls, crawl_id: str) -> tuple[bool, List[str]]:
        try:
            result = await DatabaseFactory.delete_document("crawl", crawl_id)
            if not result:
                raise NotFoundError("Crawl", crawl_id)
            return True, []
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Crawl", "delete")

class CrawlCreate(BaseModel):
    lastParsedDate: datetime | None = Field(default=None)
    parseStatus: Dict[str, Any] | None = Field(default=None)
    errorsEncountered: List[str] | None = Field(default=None)
    urlId: str = Field(...)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class CrawlUpdate(BaseModel):
    lastParsedDate: datetime | None = Field(default=None)
    parseStatus: Dict[str, Any] | None = Field(default=None)
    errorsEncountered: List[str] | None = Field(default=None)
    urlId: str | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
