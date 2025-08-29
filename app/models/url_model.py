from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Self, ClassVar, Tuple
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator, ValidationError as PydanticValidationError, BeforeValidator, Json
from app.db import DatabaseFactory
from app.config import Config
from app.services.notification import validation_warning
from app.services.request_context import RequestContext
from app.services.metadata import MetadataService
import app.models.utils as utils


class Url(BaseModel):
    id: str | None = Field(default=None)
    url: str = Field(..., pattern=r"main.url")
    params: Dict[str, Any] | None = Field(default=None)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict()

    _metadata: ClassVar[Dict[str, Any]] = {   'fields': {   'url': {   'type': 'String',
                             'required': True,
                             'pattern': {   'regex': 'main.url',
                                            'message': 'Bad URL format'}},
                  'params': {'type': 'JSON', 'required': False},
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
    'ui': {   'title': 'Url',
              'buttonLabel': 'Manage Urls',
              'description': 'Manage Event Urls'},
    'services': [],
    'uniques': []}

    class Settings:
        name = "url"

    model_config = ConfigDict(from_attributes=True, validate_by_name=True, use_enum_values=True)

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        return MetadataService.get("Url")


    @classmethod
    async def get_all(cls,
                      sort: List[Tuple[str, str]], 
                      filter: Optional[Dict[str, Any]], 
                      page: int, 
                      pageSize: int, 
                      view_spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        "Get paginated, sorted, and filtered list of entity." 
        validation = Config.validation(True)
        
        # Get filtered data from database - RequestContext provides the parameters
        response = await DatabaseFactory.get_all("Url", sort, filter, page, pageSize)
        
        if response["data"]:
            for user_dict in response["data"]:
                # Process Pydantic and FK validation if enabled
                if validation:
                    utils.validate_model(cls, user_dict, "Url")
                    await utils.validate_fks("Url", user_dict, cls._metadata)
                
                # Populate view data if requested
                if view_spec:
                    await utils.populate_view(user_dict, view_spec, "Url")
        
        return response


    @classmethod
    async def get(cls, id: str, view_spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        validation = Config.validation(False)
        
        response = await DatabaseFactory.get_by_id(str(id), "Url")
        if response["data"]:
            user_dict = response["data"]
            
            # Process Pydantic and FK validation if enabled
            if validation:
                utils.validate_model(cls, user_dict, "Url")
                await utils.validate_fks("Url", user_dict, cls._metadata)
            
            # Populate view data if requested
            if view_spec:
                await utils.populate_view(user_dict, view_spec, "Url")
        
        return response


    async def save(self, entity_id: str = '', validate: bool = True) -> tuple[Self, List[str]]:
        self.updatedAt = datetime.now(timezone.utc)

        data = self.model_dump(mode='python')

        if validate:
            # Pydantic validation
            validated_instance = utils.validate_model(self.__class__, data, "Url")
            data = validated_instance.model_dump(mode='python')
            
            # FK validation (sends notifications, doesn't throw)
            await utils.validate_fks("Url", data, self._metadata)
        
        # Unique validation (always enforced)
        unique_constraints = self._metadata.get('uniques', [])
        if unique_constraints:
            await utils.validate_uniques("Url", data, unique_constraints, entity_id if entity_id.strip() else None)

        # Save document
        response = await DatabaseFactory.save("Url", data, entity_id)
        result = response["data"]
        warnings = response.get("warnings", [])

        # Check if save was successful based on response content
        if not result:
            return self, warnings

        # Update ID from result
        if not self.id and result and isinstance(result, dict):
            extracted_id = result.get('id')
            if extracted_id:
                self.id = extracted_id

        return self, warnings

 
    @classmethod
    async def delete(cls, url_id: str) -> bool:
        return await DatabaseFactory.delete("Url", url_id)

class UrlCreate(BaseModel):
    url: str = Field(..., pattern=r"main.url")
    params: Dict[str, Any] | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )


class UrlUpdate(BaseModel):
    url: str | None = Field(default=None, pattern=r"main.url")
    params: Dict[str, Any] | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True
    )
