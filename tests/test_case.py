"""
TestCase dataclass for unified test definitions.
"""

from dataclasses import dataclass
from typing import Any, Optional, List, Dict
from enum import Enum

from attrs import field

import utils

class ResponseType(Enum):
    SINGLE = "single"  # Single object response 
    ARRAY = "array"    # Array response

@dataclass
class TestCase:
    method: str
    entity: str
    id: str
    params: str
    description: str
    expected_status: int
    fixed_data_class: type
    expected_data_len: Optional[int] = None
    expected_notification_len: Optional[int] = None
    expected_response: Optional[dict] = None  # For deep validation of single-entity responses (presence implies single response)
    expected_sort: Optional[list] = None  # List of (field, direction) tuples e.g. [('firstName', 'asc'), ('lastName', 'desc')]
    expected_filter: Optional[dict] = None  # Dict of field:value filters e.g. {'gender': 'male', 'isAccountOwner': True}
    response_type: Optional[ResponseType] = None  # Single vs array response type (auto-detected from expected_response if not set)
    expected_sub_objects: Optional[List[Dict[str, List[str]]]] = None  # Array of {'entity': [<fields>]} for each view param
    view_objects: Optional[Dict[str, Any]] = None

    url: str = field(init=False)

    def __post_init__(self):
        # construct the url
        parts = [f"/api/{self.entity}"]
        if self.id:
            parts.append(f"/{self.id}")
        if self.params:
            parts.append(f"?{self.params}")
        self.url = "".join(parts)


    def is_single(self) -> bool:
        return id == '' 

    def expected_paging(self) -> bool:
        return not id 

    def generate_expected_response(self) -> Dict[str, Any]:
        """
        Generate expected_response dynamically from test scenarios + metadata
        
        Args:
            entity_name: Name of entity (e.g., 'User', 'Account')
            entity_id: ID of the test entity
            fixed_data_class: Class containing test scenarios (e.g., FixedUsers, FixedAccounts)
            view_objects: Optional dict of view objects to include (e.g., {'account': {'exists': False}})
        
        Returns:
            Dict containing expected_response with data and warnings
        """
        if not self.id:
            return {}

        try:
            # Get test scenarios from the fixed data class
            valid_records, invalid_records = self.fixed_data_class.create_known_test_records()
            all_records = valid_records + invalid_records
            
            # Find the specific record
            entity_data = None
            for record in all_records:
                if record.get('id') == self.id:
                    entity_data = record.copy()
                    break
            
            if not entity_data:
                raise ValueError(f"Entity {self.id} not found in {self.fixed_data_class.__name__}")
            
            # Get model class dynamically
            model_class = utils.get_model_class(self.entity.capitalize())
            if not model_class:
                raise ValueError(f"Could not find model class for {self.entity.capitalize()}")
            
            # Generate expected warnings from metadata + entity data
            expected_warnings = self._generate_expected_warnings(model_class, entity_data)
            
            # Build ignore fields list from metadata
            ignore_fields = self._build_entity_ignore_fields(model_class, entity_data)
            
            # Remove ignored fields from entity data
            cleaned_data = entity_data.copy()
            for field in ignore_fields:
                cleaned_data.pop(field, None)
            
            # Add view objects if provided
            if self.view_objects:
                cleaned_data.update(self.view_objects)
            
            return {
                "data": cleaned_data,
                "warnings": expected_warnings
            }
            
        except Exception as e:
            print(f"❌ Error generating expected_response for {self.entity}/{self.entity}: {e}")
            raise
    
    def _generate_expected_warnings(self, model_class, entity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate expected validation warnings by applying model metadata to entity data
        
        Args:
            model_class: The model class (e.g., User, Account)
            entity_data: The test entity data
            
        Returns:
            List of expected warning dictionaries
        """
        warnings = []
        
        try:
            metadata = model_class.get_metadata()
            fields = metadata.get('fields', {})
            
            # Check each field for validation issues
            for field_name, field_info in fields.items():
                field_value = entity_data.get(field_name)
                
                # Check required fields
                if field_info.get('required', False) and field_value is None:
                    warnings.append({
                        "type": "validation",
                        "field": field_name,
                        "message": "Field required"
                    })
                
                # Check enum values
                if field_value is not None and 'enum' in field_info:
                    valid_values = field_info['enum'].get('values', [])
                    if valid_values and field_value not in valid_values:
                        warnings.append({
                            "type": "validation", 
                            "field": field_name
                        })
                
                # Check numeric constraints (currency, etc.)
                if field_value is not None and field_info.get('type') == 'Currency':
                    if isinstance(field_value, (int, float)) and field_value < 0:
                        warnings.append({
                            "type": "validation",
                            "field": field_name
                        })
                
                # Check email format
                if field_value is not None and field_info.get('type') == 'String' and 'email' in field_name.lower():
                    # Basic email validation - if it doesn't look like valid email
                    if isinstance(field_value, str) and '@' not in field_value:
                        warnings.append({
                            "type": "validation",
                            "field": field_name
                        })
                
                # Check FK references (ObjectId fields)
                if field_name.endswith('Id') and field_value is not None:
                    # For test scenarios, assume FK is invalid if it contains "invalid" or "nonexistent"
                    if isinstance(field_value, str) and ("invalid" in field_value or "nonexistent" in field_value):
                        warnings.append({
                            "type": "validation",
                            "field": field_name
                        })
            
            # Add password validation warning (always present for User entity)
            if hasattr(model_class, '__name__') and model_class.__name__ == 'User':
                # Password field always triggers a validation warning in test scenarios
                warnings.append({
                    "type": "validation",
                    "field": "password"
                })
            
        except Exception as e:
            print(f"❌ Error generating warnings: {e}")
        
        return warnings
    
    def _build_entity_ignore_fields(self, model_class, entity_data: Dict[str, Any]) -> List[str]:
        """Build ignore fields list from model metadata + custom ignore_fields"""
        ignore_fields = []
        
        try:
            metadata = model_class.get_metadata()
            fields = metadata.get('fields', {})
            
            # Add autogen and autoupdate fields
            for field_name, field_info in fields.items():
                if field_info.get('autoGenerate') or field_info.get('autoUpdate'):
                    ignore_fields.append(field_name)
            
            # Add custom ignore_fields from entity data
            custom_ignore = entity_data.get('ignore_fields', [])
            if custom_ignore:
                ignore_fields.extend(custom_ignore)
            
            # Always ignore ignore_fields itself
            if 'ignore_fields' not in ignore_fields:
                ignore_fields.append('ignore_fields')
                
        except Exception as e:
            print(f"❌ Error building ignore fields: {e}")
        
        return ignore_fields