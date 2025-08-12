"""
TestCase dataclass for unified test definitions.
"""

from dataclasses import dataclass, field
from utils import get_fk_entity

from typing import Any, Optional, List, Dict
from enum import Enum
import sys
from pathlib import Path

# Add project paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

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
        
        # Auto-generate expected_response if not provided and this is a single entity request
        if self.expected_response is None and self.id:
            self.expected_response = self._generate_expected_response()


    def is_single_request(self) -> bool:
        """Returns True if this is a single entity request (has ID)"""
        return bool(self.id)

    def is_list_request(self) -> bool:
        """Returns True if this is a list request (no ID)"""
        return not bool(self.id) 

    def _generate_expected_response(self) -> Dict[str, Any]:
        """Generate expected_response dynamically from test scenarios + metadata"""
        if not self.id:
            return {}
        
        try:
            # Import here to avoid circular dependencies
            import utils
            from data import BaseDataFactory
            
            # Universal lookup - works for any entity
            entity_data = BaseDataFactory.get_test_record_by_id(self.id)
            
            if not entity_data:
                return {}  # Gracefully handle missing test data
            
            # Get model class dynamically
            model_class = utils.get_model_class(self.entity.capitalize())
            
            # Generate expected warnings using entity data and metadata
            expected_warnings = self._generate_expected_warnings(entity_data, model_class)
            
            # Remove ignored fields from entity data
            cleaned_data = entity_data.copy()
            
            # Add view objects if provided
            if self.view_objects:
                cleaned_data.update(self.view_objects)
            
            return {
                "data": cleaned_data,
                "notifications": {self.id: {"warnings": expected_warnings}}
            }
            
        except Exception as e:
            # Gracefully handle any errors during generation
            return {}
    
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
                
        except Exception:
            pass  # Gracefully handle metadata errors
        
        return ignore_fields
    
    def _generate_expected_warnings(self, entity_data: Dict[str, Any], model_class) -> List[Dict[str, Any]]:
        """Generate expected validation warnings using model metadata"""
        try:
            metadata = model_class.get_metadata()
            fields = metadata.get('fields', {})
            warnings = []
            
            for field_name, field_info in fields.items():
                field_value = entity_data.get(field_name)
                
                # Required field validation
                if field_info.get('required', False) and field_value is None:
                    warnings.append({
                        "type": "validation",
                        "field": field_name,
                        "message": "Field required"
                    })
                
                # Enum validation
                if field_value is not None and 'enum' in field_info:
                    valid_values = field_info['enum'].get('values', [])
                    if valid_values and field_value not in valid_values:
                        warnings.append({
                            "type": "validation",
                            "field": field_name
                        })
                
                # Currency validation
                if field_value is not None and field_info.get('type') == 'Currency':
                    if isinstance(field_value, (int, float)) and field_value < 0:
                        warnings.append({
                            "type": "validation",
                            "field": field_name
                        })
                
                # Email validation
                if field_value is not None and field_info.get('type') == 'String' and 'email' in field_name.lower():
                    if isinstance(field_value, str) and '@' not in field_value:
                        warnings.append({
                            "type": "validation",
                            "field": field_name
                        })
                
                # FK validation
                fk_entity = get_fk_entity(field_name)
                # if self.fk_validation:
                #     warnings.append({
                #         "type": "validation",
                #         "field": field_name,
                #         "message": f"  FK value for {field_name}: {field_value} does not exist"

                #     })
            
            return warnings
            
        except Exception:
            return []  # Gracefully handle any errors