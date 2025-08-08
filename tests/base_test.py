"""
Base testing framework for Events application.
Uses the existing database abstraction layer from DatabaseFactory.
"""

import sys
import os
import json
import requests
import asyncio
import argparse
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config
from app.db import DatabaseFactory
import utils
from test_case import TestCase

@dataclass
class TestCounter:
    """Simple counter for test results with reporting"""
    passed: int = 0
    failed: int = 0
    
    @property
    def total(self) -> int:
        return self.passed + self.failed
    
    def pass_test(self):
        """Record a passing test"""
        self.passed += 1
    
    def fail_test(self):
        """Record a failing test"""
        self.failed += 1
    
    def summary(self, name: str = "") -> str:
        """Generate summary string"""
        prefix = f"{name}: " if name else ""
        return f"📊 {prefix}{self.passed} passed, {self.failed} failed, {self.total} total"

    def update(self, other: 'TestCounter'):
        """Update this counter with another counter's results"""
        self.passed += other.passed
        self.failed += other.failed
@dataclass
class TestResult:
    name: str
    status: str  # "PASS" or "FAIL"
    details: str
    duration: float = 0.0

class BaseTestFramework(ABC):
    """Base test framework that can be extended for different entities"""
    
    def __init__(self, config_file: str, server_url: str = "http://127.0.0.1:5500", verbose: bool = False, curl_file_handle = None, request_delay: float = 0.0, curl_responses: Dict = None):
        self.config_file = config_file
        self.verbose = verbose
        self.curl_file_handle = curl_file_handle
        self.request_delay = request_delay  # Delay between requests to prevent server overload
        self.curl_responses = curl_responses or {}  # Pre-captured curl responses
        self.curl_generation_only = curl_file_handle is not None and not curl_responses  # Generate curl.sh only, no HTTP requests
        self.counter = TestCounter()
        self.results: List[TestResult] = []
        self.config = {}
        
        # Note: curl file is now managed by ComprehensiveTestRunner
        
        # Load config and initialize database through existing abstraction
        if config_file and config_file.strip(): 
            self.config = Config.initialize(config_file)
            
            if self.verbose:
                print(f"✅ Loaded config from {config_file}")
        else:
            # No config file provided - use defaults
            if self.verbose:
                 print("⚠️  No config file provided - using defaults")
            self.config['fk_validation'] = ''
            self.config['db_type'] = 'mongodb'

        print(f"   Database: {self.config['db_type']}")
        print(f"   FK Validation: {self.config['fk_validation']}")

    @abstractmethod
    def get_test_cases(self) -> List[TestCase]:
        """Return all test cases for this suite - must be implemented by subclasses"""
        pass
    
    async def setup_database_connection(self):
        """Setup database connection using existing DatabaseFactory"""
        try:
            await DatabaseFactory.initialize(self.config['db_type'], self.config['db_uri'], self.config['db_name'])
            print(f"✅ Database connection established via DatabaseFactory")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    async def cleanup_database_connection(self):
        """Close database connection"""
        try:
            if DatabaseFactory.is_initialized():
                await DatabaseFactory.close()
                print("✅ Database connection closed")
        except Exception as e:
            print(f"❌ Database cleanup failed: {e}")
    
    def test(self, name: str, test_func, expected_result=None):
        """Run a test and track results"""
        print(f"\\n{'='*60}")
        print(f"TEST {self.counter.total + 1}: {name}")
        print('='*60)
        
        start_time = datetime.now()
        
        try:
            result = test_func()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if expected_result is not None:
                if result == expected_result:
                    print(f"✅ PASS: {name} ({duration:.2f}s)")
                    self.counter.pass_test()
                    self.results.append(TestResult(name, "PASS", str(result), duration))
                else:
                    print(f"❌ FAIL: {name} ({duration:.2f}s)")
                    print(f"   Expected: {expected_result}")
                    print(f"   Got: {result}")
                    self.counter.fail_test()
                    self.results.append(TestResult(name, "FAIL", f"Expected {expected_result}, got {result}", duration))
            else:
                print(f"✅ PASS: {name} ({duration:.2f}s)")
                self.counter.pass_test()
                self.results.append(TestResult(name, "PASS", str(result), duration))
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            print(f"❌ FAIL: {name} ({duration:.2f}s)")
            print(f"   Exception: {e}")
            self.counter.fail_test()
            self.results.append(TestResult(name, "FAIL", str(e), duration))
    
    def summary(self):
        """Print test summary"""
        print(f"\\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        print(f"Total tests: {self.counter.total}")
        print(f"Passed: {self.counter.passed}")
        print(f"Failed: {self.counter.failed}")
        print(f"Success rate: {(self.counter.passed/self.counter.total)*100:.1f}%" if self.counter.total > 0 else "No tests run")
        
        total_duration = sum(r.duration for r in self.results)
        print(f"Total duration: {total_duration:.2f}s")
        
        if self.counter.failed > 0:
            print(f"\\n❌ FAILED TESTS:")
            for result in self.results:
                if result.status == "FAIL":
                    print(f"  - {result.name}: {result.details}")
        
        return self.counter.failed == 0
    
    # def _init_curl_file(self):
    #     """Initialize curl.sh file in tests directory, overwriting if it exists"""
    #     try:
    #         with open('tests/curl.sh', 'w') as f:
    #             f.write('#!/bin/bash\n')
    #             f.write('# Generated curl commands from test execution\n')
    #             f.write('# Run: chmod +x tests/curl.sh && ./tests/curl.sh\n\n')
    #         print("📁 Initialized tests/curl.sh - API calls will be logged")
    #     except Exception as e:
    #         print(f"⚠️ Warning: Could not initialize tests/curl.sh: {e}")
    
    
    # def _get_decoded_url_comment(self, url: str) -> str:
    #     """Generate a comment showing decoded URL parameters"""
    #     from urllib.parse import urlparse, parse_qs, unquote
        
    #     parsed = urlparse(url)
    #     if not parsed.query:
    #         return ""
        
    #     # Parse query parameters
    #     params = parse_qs(parsed.query, keep_blank_values=True)
    #     decoded_parts = []
        
    #     for key, values in params.items():
    #         for value in values:
    #             decoded_value = unquote(value)
    #             # Only add comment if the value was actually encoded (contains special chars)
    #             if decoded_value != value and any(char in decoded_value for char in ['{', '}', ':', '"', ' ']):
    #                 decoded_parts.append(f"{key}={decoded_value}")
    #             elif decoded_value != value:
    #                 decoded_parts.append(f"{key}={decoded_value}")
        
    #     if decoded_parts:
    #         return f"Decoded parameters: {', '.join(decoded_parts)}"
        
    #     return ""
    
    # def _get_decoded_url_for_display(self, url: str) -> str:
    #     """Return URL with decoded parameters for display in echo statements"""
    #     from urllib.parse import urlparse, parse_qs, unquote, urlencode
        
    #     parsed = urlparse(url)
    #     if not parsed.query:
    #         return url
        
    #     # Parse and decode all query parameters
    #     params = parse_qs(parsed.query, keep_blank_values=True)
    #     decoded_params = {}
        
    #     for key, values in params.items():
    #         decoded_values = []
    #         for value in values:
    #             decoded_value = unquote(value)
    #             decoded_values.append(decoded_value)
    #         decoded_params[key] = decoded_values
        
    #     # Rebuild URL with decoded (readable) parameters for display
    #     readable_params = []
    #     for key, values in decoded_params.items():
    #         for value in values:
    #             readable_params.append(f"{key}={value}")
        
    #     readable_query = "&".join(readable_params)
    #     return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{readable_query}"
    
    def validate_pagination(self, response: Dict, endpoint: str = "", expected_page: int = 0, expected_per_page: int = 0) -> bool:
        """Validate GitHub-style pagination structure and values"""
        if 'pagination' not in response:
            if self.verbose:
                print(f"   ❌ Missing pagination object in response for {endpoint}")
            return False
        
        pagination = response['pagination']
        required_fields = ['page', 'per_page', 'total', 'total_pages', 'has_next', 'has_prev']
        
        for field in required_fields:
            if field not in pagination:
                if self.verbose:
                    print(f"   ❌ Missing pagination field '{field}' for {endpoint}")
                return False
        
        # Validate field types and basic logic
        if not isinstance(pagination['page'], int) or pagination['page'] < 1:
            if self.verbose:
                print(f"   ❌ Invalid page number: {pagination['page']} for {endpoint}")
            return False
        
        if not isinstance(pagination['per_page'], int) or pagination['per_page'] < 1:
            if self.verbose:
                print(f"   ❌ Invalid per_page: {pagination['per_page']} for {endpoint}")
            return False
        
        if not isinstance(pagination['total'], int) or pagination['total'] < 0:
            if self.verbose:
                print(f"   ❌ Invalid total: {pagination['total']} for {endpoint}")
            return False
        
        # Validate navigation hints make sense
        current_page = pagination['page']
        total_pages = pagination['total_pages']
        
        expected_has_prev = current_page > 1
        expected_has_next = current_page < total_pages
        
        if pagination['has_prev'] != expected_has_prev:
            if self.verbose:
                print(f"   ❌ Incorrect has_prev: {pagination['has_prev']}, expected {expected_has_prev} for {endpoint}")
            return False
        
        if pagination['has_next'] != expected_has_next:
            if self.verbose:
                print(f"   ❌ Incorrect has_next: {pagination['has_next']}, expected {expected_has_next} for {endpoint}")
            return False
        
        # Validate expected values if provided
        if expected_page and pagination['page'] != expected_page:
            if self.verbose:
                print(f"   ❌ Expected page {expected_page}, got {pagination['page']} for {endpoint}")
            return False
        
        if expected_per_page and pagination['per_page'] != expected_per_page:
            if self.verbose:
                print(f"   ❌ Expected per_page {expected_per_page}, got {pagination['per_page']} for {endpoint}")
            return False
        
        if self.verbose:
            print(f"   ✅ Pagination valid: page {pagination['page']}/{pagination['total_pages']}, {pagination['per_page']} per page, {pagination['total']} total")
        
        return True

    def make_api_request(self, method: str, endpoint: str, data: Dict = {}, expected_status: int = 200) -> Tuple[bool, Dict]:
        """Helper method for API requests"""
        url = f"{self.config['server_url']}{endpoint}"
        
        # Check if we have a pre-captured curl response for this URL
        if self.curl_responses and url in self.curl_responses:
            if self.verbose:
                print(f"🔗 Using cached curl response for: {url}")
            return self._process_curl_response(self.curl_responses[url], expected_status)
        
        # If we have curl_responses but no match, this is an error - don't make HTTP requests!
        if self.curl_responses:
            if self.verbose:
                print(f"❌ No curl response found for: {url}")
                print(f"   Available URLs: {list(self.curl_responses.keys())[:3]}...")
            return False, {"error": f"No curl response found for {url}"}
        
        # Note: curl logging is handled by the test suites via write_curl_commands_for_test_suite()
        
        # If we're in curl generation only mode, return fake success response
        if self.curl_generation_only:
            if self.verbose:
                print(f"🔗 Generated curl command for: {method} {url}")
                print(f"   📝 Saved to curl.sh - no HTTP request made")
            return True, {"curl_generation_mode": True}
        
        # Add delay between requests to prevent server overload
        if self.request_delay > 0:
            time.sleep(self.request_delay)
        
        # Verbose mode: show detailed request info
        if self.verbose:
            print(f"🔗 Testing URL: {method} {url}")
            if data:
                # Show abbreviated request data
                data_str = str(data)
                if len(data_str) > 100:
                    data_str = data_str[:97] + "..."
                print(f"   📤 Request: {data_str}")
            print(f"   ⏱️  Starting request at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}...")
        
        start_time = datetime.now()
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Calculate response time
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            # Show basic or verbose response info
            if self.verbose:
                print(f"   📥 Response: {response.status_code} {response.reason} ({duration:.0f}ms)")
                
                # Show response summary
                try:
                    json_response = response.json()
                    if 'data' in json_response and isinstance(json_response['data'], list):
                        count = len(json_response['data'])
                        print(f"   📊 Data: Retrieved {count} items")
                        if 'total_count' in json_response:
                            print(f"   📊 Total: {json_response['total_count']} total items")
                    elif 'detail' in json_response:
                        detail = json_response['detail']
                        if isinstance(detail, list) and len(detail) > 0:
                            print(f"   📊 Error: {detail[0].get('msg', str(detail[0]))}")
                        else:
                            print(f"   📊 Error: {detail}")
                    elif response.status_code >= 400:
                        print(f"   📊 Error: {response.text[:100]}")
                    elif len(response.text) < 200:
                        print(f"   📊 Response: {response.text}")
                except:
                    if len(response.text) < 100:
                        print(f"   📊 Response: {response.text}")
                
                # Show pass/fail status
                if response.status_code == expected_status:
                    print(f"   ✅ Result: PASS - Status {response.status_code} as expected")
                else:
                    print(f"   ❌ Result: FAIL - Expected {expected_status}, got {response.status_code}")
            else:
                print(f"  {method} {endpoint} -> {response.status_code}")
            
            if response.status_code == expected_status:
                try:
                    if self.verbose:
                        print(f"   🔄 Parsing JSON response ({len(response.text)} chars)...")
                    json_data = response.json()
                    if self.verbose:
                        print(f"   ✅ JSON parsed successfully")
                    return True, json_data
                except:
                    return True, {"raw_response": response.text}
            else:
                if not self.verbose:  # Only print if not already shown in verbose mode
                    print(f"  Expected {expected_status}, got {response.status_code}")
                try:
                    return False, response.json()
                except:
                    return False, {"error": response.text}
                    
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            if "timeout" in str(e).lower():
                print(f"  Request timed out after {duration:.1f}s: {e}")
            else:
                print(f"  Request failed after {duration:.1f}s: {e}")
            return False, {"exception": str(e)}
    
    def _process_curl_response(self, curl_response, expected_status: int = 200) -> Tuple[bool, Dict]:
        """Process a pre-captured curl response"""
        # Verbose mode: show curl response info
        if self.verbose:
            print(f"🔗 Using curl response: {curl_response.url}")
            print(f"   📥 Response: {curl_response.status_code} OK ({curl_response.elapsed*1000:.0f}ms)")
            print(f"   📊 Data: Retrieved from curl cache")
            print(f"   ✅ Result: {'PASS' if curl_response.status_code == expected_status else 'FAIL'} - Status {curl_response.status_code} {'as expected' if curl_response.status_code == expected_status else f'expected {expected_status}'}")
            print(f"   🔄 Parsing JSON response ({len(curl_response.text)} chars)...")
        
        # Check status code
        if curl_response.status_code != expected_status:
            if self.verbose:
                print(f"   ❌ Status code mismatch: expected {expected_status}, got {curl_response.status_code}")
            return False, {}
        
        # Parse JSON response
        try:
            json_data = curl_response.json()
            if self.verbose:
                print(f"   ✅ JSON parsed successfully")
            return True, json_data
        except Exception as e:
            if self.verbose:
                print(f"   ❌ JSON parsing error: {e}")
            return False, {}
    
    async def insert_invalid_document(self, collection_name: str, document: Dict) -> bool:
        """Insert a document directly via DatabaseFactory bypassing validation"""
        try:
            # Use DatabaseFactory to save directly, bypassing model validation
            result, warnings = await DatabaseFactory.save_document(collection_name, document, [])
            print(f"✅ Inserted invalid document directly via DatabaseFactory")
            if warnings:
                print(f"   Warnings: {warnings}")
            return True
        except Exception as e:
            print(f"❌ Failed to insert document via DatabaseFactory: {e}")
            return False
    
    async def get_document_by_id(self, collection_name: str, doc_id: str) -> Optional[Dict]:
        """Get a document directly via DatabaseFactory"""
        try:
            doc, warnings = await DatabaseFactory.get_by_id(collection_name, doc_id, [])
            if warnings:
                print(f"   Warnings on get: {warnings}")
            return doc
        except Exception as e:
            print(f"❌ Failed to get document via DatabaseFactory: {e}")
            return None
    
    async def cleanup_test_data(self, collection_name: str, filter_criteria: Dict):
        """Clean up test data via DatabaseFactory"""
        try:
            # For cleanup, we'll need to get documents first, then delete them by ID
            # This mimics the model delete behavior
            if "username" in filter_criteria:
                # Find test users by username pattern
                all_docs, warnings, count = await DatabaseFactory.get_all(collection_name, [])
                deleted_count = 0
                for doc in all_docs:
                    if any(filter_criteria[key] in str(doc.get(key, "")) for key in filter_criteria):
                        doc_id = doc.get('id')
                        if doc_id:
                            success = await DatabaseFactory.delete_document(collection_name, doc_id)
                            if success:
                                deleted_count += 1
                print(f"🧹 Cleaned up {deleted_count} test documents")
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")

  
    
    @staticmethod
    def create_argument_parser():
        """Create argument parser for tests"""
        parser = argparse.ArgumentParser(description='Events Testing Framework')
        parser.add_argument('config_file', nargs='?', default='mongo.json',
                           help='Configuration file path (default: mongo.json)')
        parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                           help='Server URL for API tests (default: http://127.0.0.1:5500)')
        parser.add_argument('--preserve', action='store_true',
                           help='Preserve test data after running tests (for troubleshooting)')
        parser.add_argument('--verbose', action='store_true',
                           help='Show detailed URL testing and response information')
        parser.add_argument('--curl', action='store_true',
                           help='Dump all API calls in curl format to curl.sh (overwrites existing file)')
        return parser
"""
TestCase dataclass for unified test definitions.
"""

# from dataclasses import dataclass
# from typing import Optional, List, Dict
# from enum import Enum

# from attrs import field

# class ResponseType(Enum):
#     SINGLE = "single"  # Single object response 
#     ARRAY = "array"    # Array response

# @dataclass
# class TestCase:
#     method: str
#     entity: str
#     id: str
#     params: str
#     description: str
#     expected_status: int
#     fixed_data_class: type
#     expected_data_len: Optional[int] = None
#     expected_notification_len: Optional[int] = None
#     expected_response: Optional[dict] = None  # For deep validation of single-entity responses (presence implies single response)
#     expected_sort: Optional[list] = None  # List of (field, direction) tuples e.g. [('firstName', 'asc'), ('lastName', 'desc')]
#     expected_filter: Optional[dict] = None  # Dict of field:value filters e.g. {'gender': 'male', 'isAccountOwner': True}
#     response_type: Optional[ResponseType] = None  # Single vs array response type (auto-detected from expected_response if not set)
#     expected_sub_objects: Optional[List[Dict[str, List[str]]]] = None  # Array of {'entity': [<fields>]} for each view param
#     view_objects: Optional[Dict[str, Any]] = None

#     url: str = field(init=False)

#     def __post_init__(self):
#         # construct the url
#         parts = [f"/api/{self.entity}"]
#         if self.id:
#             parts.append(f"/{self.id}")
#         if self.params:
#             parts.append(f"?{self.params}")
#         self.url = "".join(parts)


#     def is_single(self) -> bool:
#         return id == '' 

#     def expected_paging(self) -> bool:
#         return not id 

#     def generate_expected_response(self) -> Dict[str, Any]:
#         """
#         Generate expected_response dynamically from test scenarios + metadata
        
#         Args:
#             entity_name: Name of entity (e.g., 'User', 'Account')
#             entity_id: ID of the test entity
#             fixed_data_class: Class containing test scenarios (e.g., FixedUsers, FixedAccounts)
#             view_objects: Optional dict of view objects to include (e.g., {'account': {'exists': False}})
        
#         Returns:
#             Dict containing expected_response with data and warnings
#         """
#         if not self.id:
#             return {}

#         try:
#             # Get test scenarios from the fixed data class
#             valid_records, invalid_records = self.fixed_data_class.create_known_test_records()
#             all_records = valid_records + invalid_records
            
#             # Find the specific record
#             entity_data = None
#             for record in all_records:
#                 if record.get('id') == self.id:
#                     entity_data = record.copy()
#                     break
            
#             if not entity_data:
#                 raise ValueError(f"Entity {self.id} not found in {self.fixed_data_class.__name__}")
            
#             # Get model class dynamically
#             model_class = utils.get_model_class(self.entity.capitalize())
#             if not model_class:
#                 raise ValueError(f"Could not find model class for {self.entity.capitalize()}")
            
#             # Generate expected warnings from metadata + entity data
#             expected_warnings = self._generate_expected_warnings(model_class, entity_data)
            
#             # Build ignore fields list from metadata
#             ignore_fields = self._build_entity_ignore_fields(model_class, entity_data)
            
#             # Remove ignored fields from entity data
#             cleaned_data = entity_data.copy()
#             for field in ignore_fields:
#                 cleaned_data.pop(field, None)
            
#             # Add view objects if provided
#             if self.view_objects:
#                 cleaned_data.update(self.view_objects)
            
#             return {
#                 "data": cleaned_data,
#                 "warnings": expected_warnings
#             }
            
#         except Exception as e:
#             if self.verbose:
#                 print(f"❌ Error generating expected_response for {entity_name}/{entity_id}: {e}")
#             raise
    
#     def _generate_expected_warnings(self, model_class, entity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
#         """
#         Generate expected validation warnings by applying model metadata to entity data
        
#         Args:
#             model_class: The model class (e.g., User, Account)
#             entity_data: The test entity data
            
#         Returns:
#             List of expected warning dictionaries
#         """
#         warnings = []
        
#         try:
#             metadata = model_class.get_metadata()
#             fields = metadata.get('fields', {})
            
#             # Check each field for validation issues
#             for field_name, field_info in fields.items():
#                 field_value = entity_data.get(field_name)
                
#                 # Check required fields
#                 if field_info.get('required', False) and field_value is None:
#                     warnings.append({
#                         "type": "validation",
#                         "field": field_name,
#                         "message": "Field required"
#                     })
                
#                 # Check enum values
#                 if field_value is not None and 'enum' in field_info:
#                     valid_values = field_info['enum'].get('values', [])
#                     if valid_values and field_value not in valid_values:
#                         warnings.append({
#                             "type": "validation", 
#                             "field": field_name
#                         })
                
#                 # Check numeric constraints (currency, etc.)
#                 if field_value is not None and field_info.get('type') == 'Currency':
#                     if isinstance(field_value, (int, float)) and field_value < 0:
#                         warnings.append({
#                             "type": "validation",
#                             "field": field_name
#                         })
                
#                 # Check email format
#                 if field_value is not None and field_info.get('type') == 'String' and 'email' in field_name.lower():
#                     # Basic email validation - if it doesn't look like valid email
#                     if isinstance(field_value, str) and '@' not in field_value:
#                         warnings.append({
#                             "type": "validation",
#                             "field": field_name
#                         })
                
#                 # Check FK references (ObjectId fields)
#                 if field_name.endswith('Id') and field_value is not None:
#                     # For test scenarios, assume FK is invalid if it contains "invalid" or "nonexistent"
#                     if isinstance(field_value, str) and ("invalid" in field_value or "nonexistent" in field_value):
#                         warnings.append({
#                             "type": "validation",
#                             "field": field_name
#                         })
            
#             # Add password validation warning (always present for User entity)
#             if hasattr(model_class, '__name__') and model_class.__name__ == 'User':
#                 # Password field always triggers a validation warning in test scenarios
#                 warnings.append({
#                     "type": "validation",
#                     "field": "password"
#                 })
            
#         except Exception as e:
#             if self.verbose:
#                 print(f"❌ Error generating warnings: {e}")
        
#         return warnings
    
#     def _build_entity_ignore_fields(self, model_class, entity_data: Dict[str, Any]) -> List[str]:
#         """Build ignore fields list from model metadata + custom ignore_fields"""
#         ignore_fields = []
        
#         try:
#             metadata = model_class.get_metadata()
#             fields = metadata.get('fields', {})
            
#             # Add autogen and autoupdate fields
#             for field_name, field_info in fields.items():
#                 if field_info.get('autoGenerate') or field_info.get('autoUpdate'):
#                     ignore_fields.append(field_name)
            
#             # Add custom ignore_fields from entity data
#             custom_ignore = entity_data.get('ignore_fields', [])
#             if custom_ignore:
#                 ignore_fields.extend(custom_ignore)
            
#             # Always ignore ignore_fields itself
#             if 'ignore_fields' not in ignore_fields:
#                 ignore_fields.append('ignore_fields')
                
#         except Exception as e:
#             if self.verbose:
#                 print(f"❌ Error building ignore fields: {e}")
        
#         return ignore_fields