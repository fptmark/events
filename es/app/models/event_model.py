from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from app.db import Database
import app.utils as helpers
from app.errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError

class UniqueValidationError(Exception):
    def __init__(self, fields, query):
        self.fields = fields
        self.query = query
    def __str__(self):
        return f"Unique constraint violation for fields {self.fields}: {self.query}"


class EventBase(BaseModel):
    """Base Event model with common fields and validation"""
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    dateTime: datetime = Field(...)
    location: str = Field(..., max_length=500)
    category: str = Field(..., pattern=r'^(music|sports|arts|food|tech|other)$')
    tags: List[str] = Field(default_factory=list)
    maxAttendees: Optional[int] = Field(None, ge=1, le=10000)
    price: Optional[float] = Field(None, ge=0, le=10000)
    organizerId: str = Field(...)
    status: str = Field(..., pattern=r'^(draft|published|cancelled)$')

    @field_validator('title')
    def validate_title(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('title must be at least 3 characters')
        if len(v) > 200:
            raise ValueError('title must be at most 200 characters')
        return v

    @field_validator('description')
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError('description must be at most 2000 characters')
        return v

    @field_validator('dateTime')
    def parse_date_time(cls, v: Any) -> datetime:
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError('dateTime must be in ISO format')
        return v

    @field_validator('location')
    def validate_location(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError('location must be at most 500 characters')
        return v

    @field_validator('category')
    def validate_category(cls, v: str) -> str:
        allowed = ['music', 'sports', 'arts', 'food', 'tech', 'other']
        if v not in allowed:
            raise ValueError(f'category must be one of: {", ".join(allowed)}')
        return v

    @field_validator('tags')
    def validate_tags(cls, v: List[str]) -> List[str]:
        if len(v) > 20:
            raise ValueError('maximum 20 tags allowed')
        for tag in v:
            if len(tag) > 50:
                raise ValueError('tag must be at most 50 characters')
        return v

    @field_validator('maxAttendees')
    def validate_max_attendees(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v < 1:
                raise ValueError('maxAttendees must be at least 1')
            if v > 10000:
                raise ValueError('maxAttendees must be at most 10000')
        return v

    @field_validator('price')
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v < 0:
                raise ValueError('price must be at least 0')
            if v > 10000:
                raise ValueError('price must be at most 10000')
        return v

    @field_validator('status')
    def validate_status(cls, v: str) -> str:
        allowed = ['draft', 'published', 'cancelled']
        if v not in allowed:
            raise ValueError(f'status must be one of: {", ".join(allowed)}')
        return v

class Event(EventBase):
    """Event model for database operations"""
    id: Optional[str] = Field(default=None, alias="_id")
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description=": ['daily', 'weekly', 'monthly', 'yearly']")
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _metadata: ClassVar[Dict[str, Any]] = {
        'entity': 'Event',
        'fields': {
            'title': {
                'type': 'String',
                'required': True,
                'min_length': 3,
                'max_length': 200
            },
            'description': {
                'type': 'String',
                'required': False,
                'max_length': 2000,
                'ui': {
                    'multiline': True,
                    'rows': 4
                }
            },
            'dateTime': {
                'type': 'ISODate',
                'required': True,
                'ui': {'displayName': 'Date & Time'}
            },
            'location': {
                'type': 'String',
                'required': True,
                'max_length': 500
            },
            'category': {
                'type': 'String',
                'required': True,
                'enum': {
                    'values': ['music', 'sports', 'arts', 'food', 'tech', 'other'],
                    'message': 'must be a valid category'
                }
            },
            'tags': {
                'type': 'Array',
                'items': {
                    'type': 'String',
                    'max_length': 50
                },
                'max_items': 20
            },
            'maxAttendees': {
                'type': 'Integer',
                'required': False,
                'ge': 1,
                'le': 10000,
                'ui': {'displayName': 'Maximum Attendees'}
            },
            'price': {
                'type': 'Currency',
                'required': False,
                'ge': 0,
                'le': 10000
            },
            'organizerId': {
                'type': 'ObjectId',
                'required': True,
                'ui': {
                    'displayName': 'Organizer',
                    'show': {
                        'endpoint': 'user',
                        'displayInfo': [
                            {
                                'displayPages': 'summary',
                                'fields': ['username']
                            },
                            {
                                'displayPages': 'edit|create',
                                'fields': ['username', 'email']
                            }
                        ]
                    }
                }
            },
            'status': {
                'type': 'String',
                'required': True,
                'enum': {
                    'values': ['draft', 'published', 'cancelled'],
                    'message': 'must be draft, published, or cancelled'
                }
            },
            'url': {
                'type': 'String',
                'required': True,
                'pattern': {
                    'regex': '^https?://[^s]+$',
                    'message': 'Bad URL format'
                }
            },
            'cost': {
                'type': 'Number',
                'required': False,
                'ge': 0,
                'ui': {'displayPages': 'details'}
            },
            'numOfExpectedAttendees': {
                'type': 'Integer',
                'required': False,
                'ge': 0,
                'ui': {'displayPages': 'details'}
            },
            'recurrence': {
                'type': 'String',
                'required': False,
                'enum': {
                    'values': [
                        'daily',
                        'weekly',
                        'monthly',
                        'yearly'
                    ],
                    'message': 'Recurrence must be one of: daily, weekly, monthly, yearly'
                },
                'ui': {'displayPages': 'details'}
            },
            'createdAt': {
                'type': 'ISODate',
                'autoGenerate': True,
                'ui': {'readOnly': True, 'displayAfterField': '-1'}
            },
            'updatedAt': {
                'type': 'ISODate',
                'autoUpdate': True,
                'ui': {'readOnly': True, 'clientEdit': True, 'displayAfterField': '-1'}
            }
        },
        'operations': 'crud',
        'ui': {
            'title': 'Events',
            'buttonLabel': 'Manage Events',
            'description': 'Manage Event Details'
        }
    }

    class Settings:
        name = "event"

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('url')
    def validate_url(cls, v: str) -> str:
        if not re.match(r'^https?://[^s]+$', v):
            raise ValidationError(
                message="Invalid URL format",
                entity="Event",
                invalid_fields=[ValidationFailure("url", "URL must start with http:// or https://", v)]
            )
        return v

    @field_validator('cost')
    def validate_cost(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValidationError(
                message="Invalid cost",
                entity="Event",
                invalid_fields=[ValidationFailure("cost", "Cost must be at least 0", v)]
            )
        return v

    @field_validator('numOfExpectedAttendees')
    def validate_numOfExpectedAttendees(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValidationError(
                message="Invalid number of expected attendees",
                entity="Event",
                invalid_fields=[ValidationFailure("numOfExpectedAttendees", "Number of expected attendees must be at least 0", v)]
            )
        return v

    @field_validator('recurrence')
    def validate_recurrence(cls, v: Optional[str]) -> Optional[str]:
        allowed = ['daily', 'weekly', 'monthly', 'yearly']
        if v is not None and v not in allowed:
            raise ValidationError(
                message="Invalid recurrence value",
                entity="Event",
                invalid_fields=[ValidationFailure("recurrence", f"Recurrence must be one of: {', '.join(allowed)}", v)]
            )
        return v

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)
 
    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await Database.find_all("event", cls)
        except Exception as e:
            raise DatabaseError(str(e), "Event", "find_all")

    # Method to imitate Beanie's find() method
    @classmethod
    def find(cls):
        # This is a simple adapter to keep the API compatible
        # It provides a to_list() method that calls find_all()
        class FindAdapter:
            @staticmethod
            async def to_list():
                return await cls.find_all()

        return FindAdapter()

    # Replaces Beanie's get - uses common Database function
    @classmethod
    async def get(cls, id: str) -> Self:
        try:
            event = await Database.get_by_id("event", str(id), cls)
            if not event:
                raise NotFoundError("Event", id)
            return event
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Event", "get")

    # Replaces Beanie's save - uses common Database function
    async def save(self) -> Self:
        try:
            # Update timestamp
            self.updatedAt = datetime.now(timezone.utc)
            
            # Convert model to dict
            data = self.model_dump(exclude={"id"})
            
            # Save document
            result = await Database.save_document("event", self.id, data)
            
            # Update ID if this was a new document
            if not self.id and result and isinstance(result, dict) and result.get("_id"):
                self.id = result["_id"]
            
            return self
        except Exception as e:
            raise DatabaseError(str(e), "Event", "save")

    # Replaces Beanie's delete - uses common Database function
    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete event without ID",
                entity="Event",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await Database.delete_document("event", self.id)
            if not result:
                raise NotFoundError("Event", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "Event", "delete")

class EventCreate(EventBase):
    """Model for creating a new event"""
    pass

class EventUpdate(EventBase):
    """Model for updating an existing event"""
    pass

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class EventRead(BaseModel):
    id: str = Field(alias="_id")
    url: str = Field(..., pattern=r"^https?://[^s]+$")
    title: str = Field(..., max_length=200)
    dateTime: datetime = Field(...)
    location: Optional[str] = Field(None, max_length=200)
    cost: Optional[float] = Field(None, ge=0)
    numOfExpectedAttendees: Optional[int] = Field(None, ge=0)
    recurrence: Optional[str] = Field(None, description =": ['daily', 'weekly', 'monthly', 'yearly']")
    tags: Optional[List[str]] = Field(None)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
