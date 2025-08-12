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
    
    def __init__(self, config_file: str, server_url: str = "http://127.0.0.1:5500", verbose: bool = False, curl_file_handle = None, request_delay: float = 0.0, curl_responses: Optional[Dict] = None):
        self.config_file = config_file
        # self.server_url = server_url
        # self.verbose = verbose
        self.curl_file_handle = curl_file_handle
        self.request_delay = request_delay  # Delay between requests to prevent server overload
        self.curl_responses = curl_responses or {}  # Pre-captured curl responses
        self.curl_generation_only = curl_file_handle is not None and not curl_responses  # Generate curl.sh only, no HTTP requests
        self.counter = TestCounter()
        self.results: List[TestResult] = []
        self.config = {}
        
        # Load config and initialize database through existing abstraction
        if config_file and config_file.strip(): 
            self.config = Config.initialize(config_file)
            
            if verbose:
                print(f"✅ Loaded config from {config_file}")
        self.config['verbose'] = verbose


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
    
    @staticmethod
    def check_server_health(server_url: str, timeout: int = 5) -> bool:
        """Check if server is responding at the given URL"""
        try:
            import requests
            response = requests.get(f"{server_url}/api/metadata", timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False
    
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
