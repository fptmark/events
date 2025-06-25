from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError
import re
import logging
from app.db import DatabaseFactory
import app.utils as helpers
from app.config import Config
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError
from app.notification import notify_validation_error, NotificationType


class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query

    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class TagAffinity(BaseModel):
    id: Optional[str] = Field(default=None, alias='_id')
    tag: str = Field(..., max_length=50)
    affinity: int = Field(..., ge=-100, le=100)
    profileId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'id': {'type': 'ObjectId', 'autoGenerate': True},
                  'tag': {'type': 'String', 'required': True, 'max_length': 50},
                  'affinity': {   'type': 'Integer',
                                  'required': True,
                                  'ge': -100,
                                  'le': 100},
                  'createdAt': {   'type': 'ISODate',
                                   'autoGenerate': True,
                                   'ui': {   'readOnly': True,
                                             'displayAfterField': '-1'}},
                  'updatedAt': {   'type': 'ISODate',
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

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to normalize ID field to 'id' for API responses"""
        data = super().model_dump(**kwargs)
        # Normalize database-specific _id to generic id
        if "_id" in data:
            data["id"] = data.pop("_id")
        return data

    @field_validator('tag', mode='before')
    def validate_tag(cls, v):
        if v is not None and len(v) > 50:
            raise ValueError('tag must be at most 50 characters')
        return v
     
    @field_validator('affinity', mode='before')
    def validate_affinity(cls, v):
        if v is not None and int(v) < -100:
            raise ValueError('affinity must be at least -100')
        if v is not None and int(v) > 100:
            raise ValueError('affinity must be at most 100')
        return v
     

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def get_all(cls) -> tuple[Sequence[Self], List[ValidationError]]:
        try:
            get_validations, unique_validations = Config.validations(True)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_docs, warnings = await DatabaseFactory.get_all("tagaffinity", unique_constraints)
            
            tagaffinitys = []
            validation_errors = []
            
            # Conditional validation - validate AFTER read if requested
            if get_validations:
                for doc in raw_docs:
                    try:
                        tagaffinitys.append(cls.model_validate(doc))
                    except PydanticValidationError as e:
                        # Convert Pydantic errors to notifications
                        for error in e.errors():
                            notify_validation_error(
                                message=f"Validation failed for field '{error['loc'][-1]}': {error['msg']}",
                                entity="TagAffinity",
                                field=str(error['loc'][-1]),
                                value=error.get('input')
                            )
                            validation_errors.append(ValidationError(
                                message=f"Validation failed for field '{error['loc'][-1]}': {error['msg']}",
                                entity="TagAffinity",
                                invalid_fields=[ValidationFailure(
                                    field=str(error['loc'][-1]),
                                    message=error['msg'],
                                    value=error.get('input')
                                )]
                            ))
                        # Create instance without validation for failed docs
                        tagaffinitys.append(cls(**doc))
            else:
                tagaffinitys = [cls(**doc) for doc in raw_docs]  # NO validation
            
            # Add database warnings to validation errors
            validation_errors.extend([ValidationError(message=w, entity="TagAffinity", invalid_fields=[]) for w in warnings])
            return tagaffinitys, validation_errors
        except Exception as e:
            raise DatabaseError(str(e), "TagAffinity", "get_all")


    @classmethod
    async def get(cls, id: str) -> tuple[Self, List[str]]:
        try:
            get_validations, unique_validations = Config.validations(False)
            unique_constraints = cls._metadata.get('uniques', []) if unique_validations else []
            
            raw_doc, warnings = await DatabaseFactory.get_by_id("tagaffinity", str(id), unique_constraints)
            if not raw_doc:
                raise NotFoundError("TagAffinity", id)
            
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
                            entity="TagAffinity",
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
            raise DatabaseError(str(e), "TagAffinity", "get")

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
                        entity="TagAffinity",
                        field=str(err["loc"][-1]),
                        value=err.get("input"),
                        operation="save"
                    )
                failures = [ValidationFailure(field=str(err["loc"][-1]), message=err["msg"], value=err.get("input")) for err in e.errors()]
                raise ValidationError(message="Validation failed before save", entity="TagAffinity", invalid_fields=failures)
            
            # Save document with unique constraints - pass complete data
            result, warnings = await DatabaseFactory.save_document("tagaffinity", data, unique_constraints)

            # Update ID from result
            if not self.id and result and isinstance(result, dict) and result.get(DatabaseFactory.get_id_field()):
                self.id = result[DatabaseFactory.get_id_field()]

            return self, warnings
        except ValidationError:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            raise DatabaseError(str(e), "TagAffinity", "save")
 
    @classmethod
    async def delete(cls, tagaffinity_id: str) -> tuple[bool, List[str]]:
        if not tagaffinity_id:
            raise ValidationError(
                message="Cannot delete tagaffinity without ID",
                entity="TagAffinity",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await DatabaseFactory.delete_document("tagaffinity", tagaffinity_id)
            if not result:
                raise NotFoundError("TagAffinity", tagaffinity_id)
            return True, []
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "TagAffinity", "delete")

#from pydantic import BaseModel, Field, ConfigDict
#from typing import Optional, List, Dict, Any
#from datetime import datetime

class TagAffinityCreate(BaseModel):
  id: Optional[str] = Field(default=None, alias='_id')
  tag: str = Field(..., max_length=50)
  affinity: int = Field(..., ge=-100, le=100)
  profileId: str = Field(...)

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)


#from pydantic import BaseModel, Field, ConfigDict
#from typing import Optional, List, Dict, Any
#from datetime import datetime

class TagAffinityUpdate(BaseModel):
  id: Optional[str] = Field(default=None, alias='_id')
  tag: str = Field(..., max_length=50)
  affinity: int = Field(..., ge=-100, le=100)
  profileId: str = Field(...)

  model_config = ConfigDict(from_attributes=True, validate_by_name=True)

