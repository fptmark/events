"""
TestCase dataclass for unified test definitions.
"""

from dataclasses import dataclass, field
import re
from tests.utils import get_fk_entity, get_url_fields
from tests.data.base_data import DataFactory
from app.services.metadata import MetadataService

from typing import Any, Optional, List, Dict, Tuple
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


    def is_get_all(self) -> bool:
        url = self.url[:-1] if self.url.endswith('/') else self.url
        segments = url.split('/')
        return MetadataService.get(segments[-1], None) != None

    # def is_single_request(self) -> bool:
    #     """Returns True if this is a single entity request (has ID)"""
    #     return bool(self.id)

    # def is_list_request(self) -> bool:
    #     """Returns True if this is a list request (no ID)"""
    #     return not bool(self.id)
    
    def get_sort_criteria(self) -> List[Tuple[str, str]]:
        """Parse sort criteria from URL params. Returns list of (field, direction) tuples."""
        if not self.params:
            return []
            
        # Parse URL parameters
        from urllib.parse import parse_qs, urlparse
        parsed_url = urlparse(f"?{self.params}")
        params = parse_qs(parsed_url.query)
        
        sort_param = params.get('sort')
        if not sort_param:
            return []
            
        sort_fields = sort_param[0].split(',')
        criteria = []
        
        for field in sort_fields:
            field = field.strip()
            if field.startswith('-'):
                criteria.append((field[1:], 'desc'))
            else:
                criteria.append((field, 'asc'))
                
        return criteria
    
    def get_view_criteria(self) -> str | None:
        """Parse view criteria from URL params. Returns dict of {entity: [fields]}."""
        param_dict: Dict[str, str] = {}
        for param in self.params.split('&'):
            key, value = param.split('=', 1)
            if key == 'view':
                return value
        return None
            
        # # Parse URL parameters
        # from urllib.parse import parse_qs, urlparse
        # import json
        # parsed_url = urlparse(f"?{self.params}")
        # params = parse_qs(parsed_url.query)
        
        # view_param = params.get('view')
        # if not view_param:
        #     return {}
            
        # view_spec = view_param[0]
        
        # # Handle compact format: account(id,createdAt)
        # if '(' in view_spec and view_spec.endswith(')'):
        #     entity_part, fields_part = view_spec.split('(', 1)
        #     entity = entity_part.strip()
        #     fields_str = fields_part.rstrip(')')
        #     fields = [f.strip() for f in fields_str.split(',') if f.strip()]
        #     return {entity: fields}
        
        # # Handle JSON format: {"account":["id","createdAt"]}
        # try:
        #     view_dict = json.loads(view_spec)
        #     if isinstance(view_dict, dict):
        #         return view_dict
        # except (json.JSONDecodeError, ValueError):
        #     pass
            
        # return {}
    
    def get_filter_criteria(self) -> Dict[str, Any]:
        """Parse filter criteria from URL params. Returns dict of filter conditions."""
        if not self.params:
            return {}
            
        # Parse URL parameters
        from urllib.parse import parse_qs, urlparse
        parsed_url = urlparse(f"?{self.params}")
        params = parse_qs(parsed_url.query)
        
        filter_param = params.get('filter')
        if not filter_param:
            return {}
            
        filter_conditions = {}
        filter_pairs = filter_param[0].split(',')
        
        for pair in filter_pairs:
            pair = pair.strip()
            if ':' in pair:
                # Handle comparison operators (e.g., "dob:gte:1990-01-01")
                parts = pair.split(':', 2)
                if len(parts) == 3:
                    field, operator, value = parts
                    filter_key = f"{field}:{operator}"
                    filter_conditions[filter_key] = value
                elif len(parts) == 2:
                    field, value = parts
                    filter_conditions[field] = value
                    
        return filter_conditions


    def _generate_expected_response(self) -> Dict[str, Any]:
        """Generate expected_response dynamically from test scenarios + metadata"""
        from tests.data.validation import ValidationReporter
        if not self.id:
            return {}
        
        try:
            # Get entity metadata (initialized at framework startup)
            from app.services.metadata import MetadataService
            entity_metadata = MetadataService.get(self.entity)
            if not entity_metadata:
                ValidationReporter.report_error("Bad Entity", self.entity)
                return {}
            
            # Generate expected errors - detect bad fields
            expected_errors = []
            expected_request_warnings: List[Any] = []
            
            if self.expected_status in [200, 201]:
                for field in get_url_fields(self.url):
                    # Check if field exists in metadata
                    if field not in MetadataService.fields(self.entity):
                        expected_errors.append({'type': 'application', 'message': f'Invalid field \'{field}\' does not exist in entity'})

            entity_data = DataFactory.get_data_record(self.entity, self.id)

            # Generate expected warnings using entity data and metadata
            if self.expected_status in [200, 201]:      # Todo: Merge with above????
                expected_warnings = self._generate_expected_warnings(entity_data, entity_metadata)
            
            # check for fk view param
            # First get the entity and list of fields
            view_criteria = self.get_view_criteria()
            if view_criteria:
                pattern = r'^(\w+)\(([^)]+)\)$'
                match = re.match(pattern, view_criteria)

                # Look up the fk record
                fk_obj = {'exists': False}
                if match:
                    fk_entity = match.group(1)  # "account"
                    fk_id_field = fk_entity + 'Id'  # Use lowercase + Id pattern
                    fk_id_value = entity_data.get(fk_id_field)
                    if fk_id_value:
                        fk_data = DataFactory.get_data_record(fk_entity, fk_id_value)
                        if fk_data:
                            fk_obj = {'exists': True}
                
                            # now iterate over the fields
                            fields_str = match.group(2)  # "id, field"
                            fields = [f.strip() for f in fields_str.split(',')]  # ["id", "field"]
                            for fk_field in fields:
                                if fk_field in fk_data:
                                    fk_obj[fk_field] = fk_data[fk_field]
                                else:
                                    expected_request_warnings.append({
                                        "type": "request",
                                        "field": fk_field,
                                        "message": f"FK field '{fk_field}' not found in {fk_entity}"
                                    })
                        else:
                            expected_warnings.append({
                                "type": "validation",
                                "field": fk_id_field,
                                "message": f"FK record for {fk_entity} not found"
                            })

                        # Add the FK object to entity_data
                        entity_data[fk_entity] = fk_obj


            # Add view objects if provided
            if self.view_objects:
                entity_data.update(self.view_objects)
            
            # Use new notification structure - warnings grouped by entity/id
            response = {"data": entity_data}
            
            if expected_errors:
                response['notifications'] = {'errors': expected_errors}

            if len(expected_request_warnings):
                response['notifications']['request_warnings'] = expected_request_warnings

            if expected_warnings:
                response["notifications"] = {
                    "warnings": {
                        self.entity: {
                            self.id: expected_warnings
                        }
                    }
                }
                
            return response
            
        except Exception as e:
            # Gracefully handle any errors during generation
            return {}
    
    
    def _generate_expected_warnings(self, entity_data: Dict[str, Any], entity_metadata) -> List[Dict[str, Any]]:
        """Generate expected validation warnings using cached entity metadata"""
        try:
            warnings: List[Dict[str, Any]] = []
            
            if not entity_metadata:
                return warnings
            
            for field_name, field_info in MetadataService.fields(self.entity).items():
                field_value = entity_data.get(field_name)
                
                # Required field validation
                if field_info.get('required') and field_value is None:
                    warnings.append({
                        "type": "validation",
                        "field": field_name,
                        "message": "Field required"
                    })
                
                # Enum validation
                if field_value is not None and field_info.get('enum', {}).get('values'):
                    if field_value not in field_info.get('enum', {}).get('values', []):
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
    
    # def validate_field_names(self) -> bool:
    #     """Validate all field names in sorts, filters, and views. Returns True if valid."""
    #     valid = True
        
    #     # Validate sort fields
    #     sort_criteria = self.get_sort_criteria()
    #     for field_name, direction in sort_criteria:
    #         if not MetadataService.get(self.entity, field_name):
    #             ValidationReporter.report_error("Invalid sort field", f"{field_name}", header="  Bad Test Case")
    #             valid = False
        
    #     # Validate filter fields  
    #     filter_criteria = self.get_filter_criteria()
    #     for filter_key in filter_criteria.keys():
    #         field_name = filter_key.split(':')[0]  # Remove operator
    #         if not MetadataService.get(self.entity, field_name):
    #             ValidationReporter.report_error("Invalid filter field", f"{field_name}", header="  Bad Test Case")
    #             valid = False
        
    #     # Validate view fields (foreign entity fields)
    #     view_criteria = self.get_view_criteria()
    #     for entity_name, field_list in view_criteria.items():
    #         for field_name in field_list:
    #             # Create a mock test case for the foreign entity to validate its fields
    #             from app.services.metadata import MetadataService
    #             foreign_field_info = MetadataService.get(entity_name, field_name)
    #             if not foreign_field_info:
    #                 ValidationReporter.report_error("Invalid view field", f"{entity_name}.{field_name}", header="  Bad Test Case")
    #                 valid = False
        
    #     return valid


def get_test_suites(requested_tests: List[str]) -> Dict[str, Tuple[str, type]]:
    """Convert test case names to {display_name: test_class} dict"""
    from tests.suites.test_basic import BasicAPITester
    from tests.suites.test_view import ViewParameterTester
    from tests.suites.test_pagination import PaginationTester
    from tests.suites.test_sorting import SortingTester
    from tests.suites.test_filtering import FilteringTester
    from tests.suites.test_combinations import CombinationTester
    from tests.suites.test_lowercase_params import LowercaseParamTester
    
    available_tests: Dict[str, Tuple[str, type]] = {
        'basic': ("Basic API Tests", BasicAPITester),
        'view': ("View Parameter Tests", ViewParameterTester),
        'page': ("Pagination Tests", PaginationTester),
        'sort': ("Sorting Tests", SortingTester),
        'filter': ("Filtering Tests", FilteringTester),
        'combo': ("Combination Tests", CombinationTester),
        'lowercase': ("Lowercase Parameter Tests", LowercaseParamTester),
    }

    if requested_tests is None:
        # If no specific test cases provided, return all available tests
        return available_tests

    test_suites: Dict[str, Tuple[str, type]] = {}
    for test in requested_tests:
        if test in available_tests:
            test_suites[test] = available_tests[test]
        else:
            print(f"⚠️ Warning: Unknown test case '{test}' ignored")
    return test_suites