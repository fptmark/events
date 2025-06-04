from datetime import datetime, timezone
from typing import Optional, Dict, Any, ClassVar, Sequence, Self, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re
from app.db import Database
import app.utils as helpers
from ..errors import ValidationError, ValidationFailure, NotFoundError, DuplicateError, DatabaseError

class User(BaseModel):
    """User model for database operations"""
    # Database ID field
    id: Optional[str] = Field(default=None, alias="_id")
    
    # Model specific fields
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = None
    dob: Optional[datetime] = None
    isAccountOwner: bool = Field(...)
    netWorth: Optional[float] = Field(None, ge=0, le=10000000)
    accountId: str = Field(...)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(populate_by_name=True)

    # Field validators
    @field_validator('username')
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v

    @field_validator('email')
    def validate_email(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v

    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v

    @field_validator('firstName')
    def validate_firstName(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v

    @field_validator('lastName')
    def validate_lastName(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v

    @field_validator('gender')
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = ['male', 'female', 'other']
            if v not in allowed:
                raise ValueError('must be male or female')
        return v

    @field_validator('dob')
    def parse_dob(cls, v: Any) -> Optional[datetime]:
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError('Date must be in ISO format')
        return v

    # Metadata with uniqueness constraints
    _metadata: ClassVar[Dict[str, Any]] = {
        'entity': 'User',
        'uniques': [
            ['username'],  # Single field unique constraint
            ['email'],     # Single field unique constraint
            # Could add composite uniques like: ['firstName', 'lastName', 'dob']
        ],
        'fields': {
            'username': {
                'type': 'String',
                'required': True,
                'min_length': 3,
                'max_length': 50
            },
            'email': {
                'type': 'String',
                'required': True,
                'min_length': 8,
                'max_length': 50,
                'pattern': {
                    'regex': '^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$',
                    'message': 'Bad email address format'
                }
            },
            'password': {
                'type': 'String',
                'required': True,
                'min_length': 8,
                'ui': {
                    'displayPages': 'details',
                    'display': 'secret'
                }
            },
            'firstName': {
                'type': 'String',
                'required': True,
                'min_length': 3,
                'max_length': 100,
                'ui': {'displayName': 'First Name'}
            },
            'lastName': {
                'type': 'String',
                'required': True,
                'min_length': 3,
                'max_length': 100,
                'ui': {'displayName': 'Last Name'}
            },
            'gender': {
                'type': 'String',
                'required': False,
                'enum': {
                    'values': ['male', 'female', 'other'],
                    'message': 'must be male or female'
                }
            },
            'dob': {'type': 'ISODate', 'required': False},
            'isAccountOwner': {
                'type': 'Boolean',
                'required': True,
                'ui': {'displayName': 'Owner'}
            },
            'netWorth': {'type': 'Currency', 'ge': 0, 'le': 10000000},
            'accountId': {
                'type': 'ObjectId',
                'ui': {
                    'displayName': 'Account',
                    'show': {
                        'endpoint': 'account',
                        'displayInfo': [
                            {
                                'displayPages': 'summary',
                                'fields': ['createdAt']
                            },
                            {
                                'displayPages': 'edit|create',
                                'fields': ['createdAt', 'expiredAt']
                            }
                        ]
                    }
                },
                'required': True
            }
        },
        'operations': 'rcu',
        'ui': {
            'title': 'Users',
            'buttonLabel': 'Manage Users',
            'description': 'Manage User Profile'
        }
    }

    class Settings:
        name = "user"

    # Database operations
    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls._metadata)

    @classmethod
    async def find_all(cls) -> Sequence[Self]:
        try:
            return await Database.find_all("user", cls)
        except Exception as e:
            raise DatabaseError(str(e), "User", "find_all")

    @classmethod
    async def get(cls, id: str) -> Self:
        try:
            user = await Database.get_by_id("user", str(id), cls)
            if not user:
                raise NotFoundError("User", id)
            return user
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "get")

    @classmethod
    async def check_unique_constraints(cls, data: Dict[str, Any], exclude_id: Optional[str] = None) -> None:
        """Check uniqueness constraints using ES bool queries"""
        try:
            es = Database.client()
            
            # Check each unique constraint set
            for unique_fields in cls._metadata['uniques']:
                # Build terms for all fields in this unique constraint
                must_terms = []
                for field in unique_fields:
                    if field not in data:
                        # Skip this constraint if we don't have all fields
                        break
                    must_terms.append({"term": {field: data[field]}})
                
                if len(must_terms) != len(unique_fields):
                    # Skip if we didn't get all fields for this constraint
                    continue

                # Build the ES query
                query = {
                    "bool": {
                        "must": must_terms
                    }
                }

                # Add exclusion for updates
                if exclude_id:
                    query["bool"]["must_not"] = [
                        {"term": {"_id": exclude_id}}
                    ]

                # Execute targeted search
                res = await es.search(
                    index="user",
                    query=query,
                    size=1  # We only need to know if any exist
                )

                hits = res.get("hits", {}).get("hits", [])
                if hits:
                    # Determine which field value caused the duplicate
                    duplicate_values = {
                        field: data[field] 
                        for field in unique_fields
                    }
                    raise ValidationError(
                        message=f"Duplicate values found: {duplicate_values}",
                        entity="User",
                        invalid_fields=[
                            ValidationFailure(
                                field=field,
                                message="Value must be unique",
                                value=data[field]
                            )
                            for field in unique_fields
                        ]
                    )

        except ValidationError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "check_unique")

    async def save(self) -> Self:
        """Save with uniqueness checks"""
        try:
            data = self.model_dump(exclude={"id"})
            
            # Check unique constraints first
            await self.check_unique_constraints(data, exclude_id=self.id)
            
            # If no duplicates found, proceed with save
            self.updatedAt = datetime.now(timezone.utc)
            result = await Database.save_document("user", self.id, data)
            
            if not self.id and result and isinstance(result, dict):
                self.id = result.get("_id")
            return self
        except Exception as e:
            # Handle database-specific uniqueness errors
            if isinstance(e, DatabaseError) and "duplicate key" in str(e).lower():
                # For databases with native unique constraints
                raise ValidationError(
                    message="Duplicate key error from database",
                    entity="User",
                    invalid_fields=[
                        ValidationFailure(
                            field="unknown",
                            message="Value must be unique",
                            value=None
                        )
                    ]
                )
            raise DatabaseError(str(e), "User", "save")

    async def delete(self) -> bool:
        if not self.id:
            raise ValidationError(
                message="Cannot delete user without ID",
                entity="User",
                invalid_fields=[ValidationFailure("id", "ID is required for deletion", None)]
            )
        try:
            result = await Database.delete_document("user", self.id)
            if not result:
                raise NotFoundError("User", self.id)
            return True
        except NotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(str(e), "User", "delete")

class UserCreate(BaseModel):
    """Model for creating a new user"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = None
    dob: Optional[datetime] = None
    isAccountOwner: bool = Field(...)
    netWorth: Optional[float] = Field(None, ge=0, le=10000000)
    accountId: str = Field(...)

    model_config = ConfigDict(populate_by_name=True)

    # Duplicate validators for create operations
    @field_validator('username')
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v

    @field_validator('email')
    def validate_email(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v

    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v

    @field_validator('firstName')
    def validate_firstName(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v

    @field_validator('lastName')
    def validate_lastName(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v

    @field_validator('gender')
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = ['male', 'female', 'other']
            if v not in allowed:
                raise ValueError('must be male or female')
        return v

    @field_validator('dob')
    def parse_dob(cls, v: Any) -> Optional[datetime]:
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError('Date must be in ISO format')
        return v

class UserUpdate(BaseModel):
    """Model for updating an existing user"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = None
    dob: Optional[datetime] = None
    isAccountOwner: bool = Field(...)
    netWorth: Optional[float] = Field(None, ge=0, le=10000000)
    accountId: str = Field(...)

    model_config = ConfigDict(populate_by_name=True)

    # Duplicate validators for update operations
    @field_validator('username')
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v

    @field_validator('email')
    def validate_email(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v

    @field_validator('password')
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v

    @field_validator('firstName')
    def validate_firstName(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v

    @field_validator('lastName')
    def validate_lastName(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v

    @field_validator('gender')
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = ['male', 'female', 'other']
            if v not in allowed:
                raise ValueError('must be male or female')
        return v

    @field_validator('dob')
    def parse_dob(cls, v: Any) -> Optional[datetime]:
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError('Date must be in ISO format')
        return v

class UserRead(BaseModel):
    """Model for API responses"""
    id: str = Field(alias="_id")
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50)
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = None
    dob: Optional[datetime] = None
    isAccountOwner: bool = Field(...)
    netWorth: Optional[float] = Field(None, ge=0, le=10000000)
    accountId: str = Field(...)
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
