from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar
from pydantic import BaseModel, Field, ConfigDict, field_validator
from beanie import PydanticObjectId
from elasticsearch import NotFoundError
import re
from db import Database
import app.utils as helpers

class UserBaseModel(BaseModel):
    __index__ = "user"
    __unique__ = [["username"], ["email"]]
    __mappings__ = {   'accountId': {'type': 'keyword'},
    'createdAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'dob': {'format': 'strict_date_optional_time', 'type': 'date'},
    'email': {   'fields': {   'keyword': {   'ignore_above': 256,
                                              'type': 'keyword'}},
                 'type': 'text'},
    'firstName': {   'fields': {   'keyword': {   'ignore_above': 256,
                                                  'type': 'keyword'}},
                     'type': 'text'},
    'gender': {   'fields': {   'keyword': {   'ignore_above': 256,
                                               'type': 'keyword'}},
                  'type': 'text'},
    'isAccountOwner': {'type': 'boolean'},
    'lastName': {   'fields': {   'keyword': {   'ignore_above': 256,
                                                 'type': 'keyword'}},
                    'type': 'text'},
    'password': {   'fields': {   'keyword': {   'ignore_above': 256,
                                                 'type': 'keyword'}},
                    'type': 'text'},
    'updatedAt': {'format': 'strict_date_optional_time', 'type': 'date'},
    'username': {   'fields': {   'keyword': {   'ignore_above': 256,
                                                 'type': 'keyword'}},
                    'type': 'text'}}

    model_config = ConfigDict(populate_by_name=True)

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def _id(self) -> Optional[str]:
        return self.id
    @_id.setter
    def _id(self, value: Optional[str]) -> None:
        self.id = value
    async def save(self):
        # get the Elasticsearch client
        es = Database.get_es_client()
        if not es:
            raise RuntimeError("Elasticsearch client not initialized — did you forget to call Database.init()?")
     
        # save any autoupdate fields
        self.updatedAt = datetime.now(timezone.utc)
        # serialize & index
        body = self.model_dump(by_alias=True, exclude={"id"})
        resp = await es.index(
            index=self.__index__,
            id=self.id,
            document=body,
            refresh="wait_for",
        )
        self.id = resp["_id"]
        return self

class User(UserBaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
 
    __ui_metadata__: ClassVar[Dict[str, Any]] = {   'entity': 'User',
    'fields': {   'accountId': {   'displayName': 'accountId',
                                   'readOnly': True,
                                   'required': True,
                                   'type': 'ObjectId'},
                  'createdAt': {   'autoGenerate': True,
                                   'type': 'ISODate',
                                   'ui': {   'displayAfterField': '-1',
                                             'displayPages': 'summary',
                                             'readOnly': True}},
                  'dob': {'required': False, 'type': 'ISODate'},
                  'email': {   'max_length': 50,
                               'min_length': 8,
                               'pattern': {   'message': 'Bad email address '
                                                         'format',
                                              'regex': '^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$'},
                               'required': True,
                               'type': 'String'},
                  'firstName': {   'max_length': 100,
                                   'min_length': 3,
                                   'required': True,
                                   'type': 'String',
                                   'ui': {'displayName': 'First Name'}},
                  'gender': {   'enum': {   'message': 'must be male or female',
                                            'values': [   'male',
                                                          'female',
                                                          'other']},
                                'required': False,
                                'type': 'String'},
                  'isAccountOwner': {   'required': True,
                                        'type': 'Boolean',
                                        'ui': {'displayName': 'Owner'}},
                  'lastName': {   'max_length': 100,
                                  'min_length': 3,
                                  'required': True,
                                  'type': 'String',
                                  'ui': {'displayName': 'Last Name'}},
                  'password': {   'min_length': 8,
                                  'required': True,
                                  'type': 'String',
                                  'ui': {   'display': 'secret',
                                            'displayPages': 'details'}},
                  'updatedAt': {   'autoUpdate': True,
                                   'type': 'ISODate',
                                   'ui': {   'clientEdit': True,
                                             'displayAfterField': '-2',
                                             'readOnly': True}},
                  'username': {   'max_length': 50,
                                  'min_length': 3,
                                  'required': True,
                                  'type': 'String'}},
    'operations': 'rcu',
    'ui': {   'buttonLabel': 'Manage Users',
              'description': 'Manage User Profile',
              'title': 'Users'}}

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return helpers.get_metadata(cls.__ui_metadata__)
 
    @classmethod
    def _from_es_hit(cls, hit: dict) -> "User":
        data = hit["_source"]
        data["id"] = hit["_id"]
        return cls(**data)

    @classmethod
    async def get(cls, item_id: str):
        es = Database.get_es_client()
        if not es:
            raise RuntimeError("Elasticsearch client not initialized — did you forget to call Database.init()?")
        try:
            result = await es.get(index=cls.__index__, id=item_id)
            return cls._from_es_hit(result.body)
        except Exception:
            return None

    @classmethod
    async def find_all(cls) -> List[Self]:
        es = Database.get_es_client()
        if not es:
            raise RuntimeError("Elasticsearch client not initialized — did you forget to call Database.init()?")
        try:
            result = await es.search(index=cls.__index__, query={"match_all": {}}, size=1000)
            return [cls._from_es_hit(hit) for hit in result["hits"]["hits"]] #type: ignore[return-value]
        except NotFoundError:
            return []  # Return empty list if index doesn't exist

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)

    @field_validator('username', mode='before')
    def validate_username(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if v is not None and len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v
     
    @field_validator('email', mode='before')
    def validate_email(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if v is not None and len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v
     
    @field_validator('password', mode='before')
    def validate_password(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v
     
    @field_validator('firstName', mode='before')
    def validate_firstName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v
     
    @field_validator('lastName', mode='before')
    def validate_lastName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v
     
    @field_validator('gender', mode='before')
    def validate_gender(cls, v):
        _custom = {}
        allowed = ['male', 'female', 'other']
        if v is not None and v not in allowed:
            raise ValueError('must be male or female')
        return v
     
    @field_validator('dob', mode='before')
    def parse_dob(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserUpdate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)

    @field_validator('username', mode='before')
    def validate_username(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('username must be at least 3 characters')
        if v is not None and len(v) > 50:
            raise ValueError('username must be at most 50 characters')
        return v
     
    @field_validator('email', mode='before')
    def validate_email(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError('email must be at least 8 characters')
        if v is not None and len(v) > 50:
            raise ValueError('email must be at most 50 characters')
        if v is not None and not re.match(r'^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$', v):
            raise ValueError('Bad email address format')
        return v
     
    @field_validator('password', mode='before')
    def validate_password(cls, v):
        _custom = {}
        if v is not None and len(v) < 8:
            raise ValueError('password must be at least 8 characters')
        return v
     
    @field_validator('firstName', mode='before')
    def validate_firstName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('firstName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('firstName must be at most 100 characters')
        return v
     
    @field_validator('lastName', mode='before')
    def validate_lastName(cls, v):
        _custom = {}
        if v is not None and len(v) < 3:
            raise ValueError('lastName must be at least 3 characters')
        if v is not None and len(v) > 100:
            raise ValueError('lastName must be at most 100 characters')
        return v
     
    @field_validator('gender', mode='before')
    def validate_gender(cls, v):
        _custom = {}
        allowed = ['male', 'female', 'other']
        if v is not None and v not in allowed:
            raise ValueError('must be male or female')
        return v
     
    @field_validator('dob', mode='before')
    def parse_dob(cls, v):
        if v in (None, '', 'null'):
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v

    model_config = ConfigDict(from_attributes=True, validate_by_name=True)

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserRead(BaseModel):
    id: str = Field(alias="_id")
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=8, max_length=50, pattern=r"^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    firstName: str = Field(..., min_length=3, max_length=100)
    lastName: str = Field(..., min_length=3, max_length=100)
    gender: Optional[str] = Field(None, description ="must be male or female")
    dob: Optional[datetime] = Field(None)
    isAccountOwner: bool = Field(...)
    accountId: PydanticObjectId = Field(...)

    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
