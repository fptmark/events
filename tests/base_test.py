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
import app.utils as utils
from tests.test_case import TestCase

@dataclass
class TestResult:
    name: str
    status: str  # "PASS" or "FAIL"
    details: str
    duration: float = 0.0

class BaseTestFramework(ABC):
    """Base test framework that can be extended for different entities"""
    
    def __init__(self, config_file: str, server_url: str = "http://127.0.0.1:5500", verbose: bool = False, curl_file_handle = None, request_delay: float = 0.0, curl_responses: Dict = None, fk_validation: bool = None):
        self.config_file = config_file
        self.server_url = server_url
        self.verbose = verbose
        self.curl_file_handle = curl_file_handle
        self.request_delay = request_delay  # Delay between requests to prevent server overload
        self.curl_responses = curl_responses or {}  # Pre-captured curl responses
        self.curl_generation_only = curl_file_handle is not None and not curl_responses  # Generate curl.sh only, no HTTP requests
        self.test_count = 0
        self.passed = 0
        self.failed = 0
        self.results: List[TestResult] = []
        self.fk_validation = fk_validation  # Override FK validation state for validation mode
        
        # Note: curl file is now managed by ComprehensiveTestRunner
        
        # Load config and initialize database through existing abstraction
        if config_file and config_file.strip():
            self.config = Config.initialize(config_file)
            self.db_type = self.config.get('database', 'mongodb')
            self.db_uri = self.config.get('db_uri', '')
            self.db_name = self.config.get('db_name', '')
            
            if self.verbose:
                print(f"✅ Loaded config from {config_file}")
                print(f"   Database: {self.db_type}")
                print(f"   DB URI: {self.db_uri}")
                print(f"   DB Name: {self.db_name}")
        else:
            # No config file provided - use defaults
            self.config = {}
            self.db_type = 'mongodb'
            self.db_uri = ''
            self.db_name = ''
            if curl_responses and fk_validation is not None:
                # Validation mode: set FK validation state from parameter
                self.config = {'fk_validation': fk_validation}
                if self.verbose:
                    print(f"📋 Validation mode: FK validation {'ON' if fk_validation else 'OFF'}")
            elif self.verbose and curl_file_handle is None:
                print("⚠️  No config file provided - using defaults")
    
    @abstractmethod
    def get_test_cases(self) -> List[TestCase]:
        """Return all test cases for this suite - must be implemented by subclasses"""
        pass
    
    async def setup_database_connection(self):
        """Setup database connection using existing DatabaseFactory"""
        try:
            await DatabaseFactory.initialize(self.db_type, self.db_uri, self.db_name)
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
        self.test_count += 1
        print(f"\\n{'='*60}")
        print(f"TEST {self.test_count}: {name}")
        print('='*60)
        
        start_time = datetime.now()
        
        try:
            result = test_func()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if expected_result is not None:
                if result == expected_result:
                    print(f"✅ PASS: {name} ({duration:.2f}s)")
                    self.passed += 1
                    self.results.append(TestResult(name, "PASS", str(result), duration))
                else:
                    print(f"❌ FAIL: {name} ({duration:.2f}s)")
                    print(f"   Expected: {expected_result}")
                    print(f"   Got: {result}")
                    self.failed += 1
                    self.results.append(TestResult(name, "FAIL", f"Expected {expected_result}, got {result}", duration))
            else:
                print(f"✅ PASS: {name} ({duration:.2f}s)")
                self.passed += 1
                self.results.append(TestResult(name, "PASS", str(result), duration))
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            print(f"❌ FAIL: {name} ({duration:.2f}s)")
            print(f"   Exception: {e}")
            self.failed += 1
            self.results.append(TestResult(name, "FAIL", str(e), duration))
    
    def summary(self):
        """Print test summary"""
        print(f"\\n{'='*60}")
        print("TEST SUMMARY")
        print('='*60)
        print(f"Total tests: {self.test_count}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {(self.passed/self.test_count)*100:.1f}%" if self.test_count > 0 else "No tests run")
        
        total_duration = sum(r.duration for r in self.results)
        print(f"Total duration: {total_duration:.2f}s")
        
        if self.failed > 0:
            print(f"\\n❌ FAILED TESTS:")
            for result in self.results:
                if result.status == "FAIL":
                    print(f"  - {result.name}: {result.details}")
        
        return self.failed == 0
    
    def _init_curl_file(self):
        """Initialize curl.sh file in tests directory, overwriting if it exists"""
        try:
            with open('tests/curl.sh', 'w') as f:
                f.write('#!/bin/bash\n')
                f.write('# Generated curl commands from test execution\n')
                f.write('# Run: chmod +x tests/curl.sh && ./tests/curl.sh\n\n')
            print("📁 Initialized tests/curl.sh - API calls will be logged")
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize tests/curl.sh: {e}")
    
    
    def _get_decoded_url_comment(self, url: str) -> str:
        """Generate a comment showing decoded URL parameters"""
        from urllib.parse import urlparse, parse_qs, unquote
        
        parsed = urlparse(url)
        if not parsed.query:
            return ""
        
        # Parse query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)
        decoded_parts = []
        
        for key, values in params.items():
            for value in values:
                decoded_value = unquote(value)
                # Only add comment if the value was actually encoded (contains special chars)
                if decoded_value != value and any(char in decoded_value for char in ['{', '}', ':', '"', ' ']):
                    decoded_parts.append(f"{key}={decoded_value}")
                elif decoded_value != value:
                    decoded_parts.append(f"{key}={decoded_value}")
        
        if decoded_parts:
            return f"Decoded parameters: {', '.join(decoded_parts)}"
        
        return ""
    
    def _get_decoded_url_for_display(self, url: str) -> str:
        """Return URL with decoded parameters for display in echo statements"""
        from urllib.parse import urlparse, parse_qs, unquote, urlencode
        
        parsed = urlparse(url)
        if not parsed.query:
            return url
        
        # Parse and decode all query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)
        decoded_params = {}
        
        for key, values in params.items():
            decoded_values = []
            for value in values:
                decoded_value = unquote(value)
                decoded_values.append(decoded_value)
            decoded_params[key] = decoded_values
        
        # Rebuild URL with decoded (readable) parameters for display
        readable_params = []
        for key, values in decoded_params.items():
            for value in values:
                readable_params.append(f"{key}={value}")
        
        readable_query = "&".join(readable_params)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{readable_query}"
    
    def validate_pagination(self, response: Dict, endpoint: str = "", expected_page: int = None, expected_per_page: int = None) -> bool:
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

    def make_api_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> Tuple[bool, Dict]:
        """Helper method for API requests"""
        url = f"{self.server_url}{endpoint}"
        
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