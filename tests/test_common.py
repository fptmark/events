#!/usr/bin/env python3
"""
Common utilities for comprehensive test suite.

This module provides shared functionality across all test modules:
- API request handling with validation
- Logging and reporting
- curl.sh generation (one mode only)
- Response validation
- Test data setup/cleanup
- 4-mode testing infrastructure
"""

import sys
import json
import requests
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config
from app.db import DatabaseFactory
import app.utils as utils

class TestMode(Enum):
    """Test execution modes"""
    MONGODB_VALIDATION_ON = "mongodb_on"
    MONGODB_VALIDATION_OFF = "mongodb_off"
    ELASTICSEARCH_VALIDATION_ON = "elasticsearch_on"
    ELASTICSEARCH_VALIDATION_OFF = "elasticsearch_off"

@dataclass
class DatabaseConfig:
    """Database configuration for each test mode"""
    database: str
    db_uri: str
    db_name: str
    fk_validation: str
    unique_validation: bool

@dataclass
class TestResult:
    """Test result data structure"""
    name: str
    status: str  # "PASS" or "FAIL"
    details: str
    duration: float = 0.0
    mode: Optional[TestMode] = None

@dataclass
class APIResponse:
    """API response wrapper"""
    status_code: int
    json_data: Optional[Dict[Any, Any]]
    text: str
    headers: Dict[str, str]
    duration: float

class TestDataManager:
    """Manages test data creation and cleanup"""
    
    @staticmethod
    def get_test_accounts() -> List[Dict[str, Any]]:
        """Get valid test account data"""
        return [
            {
                "_id": "507f1f77bcf86cd799439011",
                "name": "primary_account",
                "description": "Primary test account",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            },
            {
                "_id": "507f1f77bcf86cd799439012", 
                "name": "secondary_account",
                "description": "Secondary test account", 
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }
        ]
    
    @staticmethod
    def get_valid_users() -> List[Dict[str, Any]]:
        """Get users with valid foreign keys"""
        timestamp = int(time.time() * 1000000)
        return [
            {
                "_id": "valid_all_user_123456",
                "username": f"valid_all_{timestamp}",
                "email": f"valid_all_{timestamp}@test.com",
                "password": "password123",
                "firstName": "Valid",
                "lastName": "AllFields",
                "gender": "male",
                "netWorth": 50000.0,
                "dob": "1990-01-15",
                "isAccountOwner": True,
                "accountId": "507f1f77bcf86cd799439011",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            },
            {
                "_id": "valid_fk_only_user_123456",
                "username": f"valid_fk_{timestamp}",
                "email": f"valid_fk_{timestamp}@test.com", 
                "password": "password123",
                "firstName": "Valid",
                "lastName": "FKOnly",
                "gender": "female",
                "netWorth": 25000.0,
                "isAccountOwner": False,
                "accountId": "507f1f77bcf86cd799439012",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }
        ]
    
    @staticmethod
    def get_invalid_fk_users() -> List[Dict[str, Any]]:
        """Get users with invalid foreign keys"""
        timestamp = int(time.time() * 1000000)
        return [
            {
                "_id": "bad_fk_user_123456",
                "username": f"bad_fk_{timestamp}",
                "email": f"bad_fk_{timestamp}@test.com",
                "password": "password123", 
                "firstName": "Bad",
                "lastName": "ForeignKey",
                "gender": "male",
                "netWorth": 30000.0,
                "isAccountOwner": False,
                "accountId": "nonexistent_account_id",  # Invalid FK
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            },
            {
                "_id": "multiple_errors_user_123456", 
                "username": f"multi_err_{timestamp}",
                "email": f"multi_err_{timestamp}@test.com",
                "password": "password123",
                "firstName": "Multiple", 
                "lastName": "Errors",
                "gender": "invalid_gender",  # Invalid enum
                "netWorth": -5000.0,  # Invalid range
                "isAccountOwner": False,
                "accountId": "another_nonexistent_id",  # Invalid FK
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }
        ]
    
    @staticmethod
    def get_validation_error_users() -> List[Dict[str, Any]]:
        """Get users with validation issues (enum, currency, etc.)"""
        timestamp = int(time.time() * 1000000)
        return [
            {
                "_id": "bad_enum_user_123456",
                "username": f"bad_enum_{timestamp}",
                "email": f"bad_enum_{timestamp}@test.com",
                "password": "password123",
                "firstName": "Bad",
                "lastName": "Enum",
                "gender": "unknown",  # Invalid enum value
                "netWorth": 15000.0,
                "isAccountOwner": False,
                "accountId": "507f1f77bcf86cd799439011",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            },
            {
                "_id": "bad_currency_user_123456",
                "username": f"bad_currency_{timestamp}",
                "email": f"bad_currency_{timestamp}@test.com",
                "password": "password123",
                "firstName": "Bad",
                "lastName": "Currency",
                "gender": "female",
                "netWorth": 99999999.0,  # Exceeds 10M limit
                "isAccountOwner": True,
                "accountId": "507f1f77bcf86cd799439012",
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }
        ]

class ConfigManager:
    """Manages test configurations for different modes"""
    
    @staticmethod
    def get_mode_configs() -> Dict[TestMode, DatabaseConfig]:
        """Get database configurations for all test modes"""
        return {
            TestMode.MONGODB_VALIDATION_ON: DatabaseConfig(
                database="mongodb",
                db_uri="mongodb://localhost:27017",
                db_name="eventMgr",
                fk_validation="multiple",
                unique_validation=True
            ),
            TestMode.MONGODB_VALIDATION_OFF: DatabaseConfig(
                database="mongodb", 
                db_uri="mongodb://localhost:27017",
                db_name="eventMgr",
                fk_validation="",
                unique_validation=False
            ),
            TestMode.ELASTICSEARCH_VALIDATION_ON: DatabaseConfig(
                database="elasticsearch",
                db_uri="http://localhost:9200",
                db_name="eventMgr", 
                fk_validation="multiple",
                unique_validation=True
            ),
            TestMode.ELASTICSEARCH_VALIDATION_OFF: DatabaseConfig(
                database="elasticsearch",
                db_uri="http://localhost:9200", 
                db_name="eventMgr",
                fk_validation="",
                unique_validation=False
            )
        }
    
    @staticmethod
    def create_temp_config(mode: TestMode) -> str:
        """Create temporary config file for a test mode"""
        configs = ConfigManager.get_mode_configs()
        config_data = configs[mode]
        
        config_dict = {
            "database": config_data.database,
            "db_uri": config_data.db_uri,
            "db_name": config_data.db_name,
            "fk_validation": config_data.fk_validation,
            "unique_validation": config_data.unique_validation
        }
        
        filename = f"tests/temp_{mode.value}_config.json"
        with open(filename, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        return filename

class APIClient:
    """HTTP client for API testing with curl generation and validation"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:5500", verbose: bool = False, curl_file: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.curl_file = curl_file
        self.session = requests.Session()
        
        # Initialize curl file if provided
        if self.curl_file:
            self._init_curl_file()
    
    def _init_curl_file(self):
        """Initialize curl.sh file with header"""
        if self.curl_file:
            with open(self.curl_file, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write("# Generated curl commands for API testing\n")
                f.write(f"# Generated on {datetime.now().isoformat()}\n\n")
    
    def _log_curl_command(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, data: Optional[str] = None):
        """Log curl command to file"""
        if not self.curl_file:
            return
            
        curl_cmd = f"curl -X {method.upper()}"
        
        if headers:
            for key, value in headers.items():
                curl_cmd += f" -H '{key}: {value}'"
        
        if data:
            curl_cmd += f" -d '{data}'"
        
        curl_cmd += f" '{url}'\n"
        
        with open(self.curl_file, 'a') as f:
            f.write(f"# {method.upper()} {url}\n")
            f.write(curl_cmd)
            f.write("\n")
    
    def request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
                timeout: int = 30) -> APIResponse:
        """Make HTTP request with logging and validation"""
        url = f"{self.base_url}{endpoint}"
        
        # Prepare headers
        if headers is None:
            headers = {}
        if 'Content-Type' not in headers and data:
            headers['Content-Type'] = 'application/json'
        
        # Prepare data
        json_data = None
        data_str = None
        if data:
            json_data = data
            data_str = json.dumps(data)
        
        # Log curl command
        self._log_curl_command(method, url, headers, data_str)
        
        # Make request with timing
        start_time = time.time()
        
        try:
            if self.verbose:
                print(f"  🌐 {method.upper()} {endpoint}")
                if params:
                    print(f"     Params: {params}")
                if data:
                    print(f"     Data: {json.dumps(data, indent=2)}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            # Parse response
            json_response = None
            try:
                json_response = response.json()
            except:
                pass
            
            api_response = APIResponse(
                status_code=response.status_code,
                json_data=json_response,
                text=response.text,
                headers=dict(response.headers),
                duration=duration
            )
            
            if self.verbose:
                print(f"     Response: {response.status_code} ({duration*1000:.0f}ms)")
                if json_response:
                    print(f"     JSON: {json.dumps(json_response, indent=2)}")
            
            return api_response
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"  ❌ Request failed: {e}")
            return APIResponse(
                status_code=0,
                json_data=None,
                text=str(e),
                headers={},
                duration=duration
            )
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """GET request"""
        return self.request('GET', endpoint, params=params, **kwargs)
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """POST request"""
        return self.request('POST', endpoint, data=data, **kwargs)
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """PUT request"""
        return self.request('PUT', endpoint, data=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> APIResponse:
        """DELETE request"""
        return self.request('DELETE', endpoint, **kwargs)

class ResponseValidator:
    """Validates API responses"""
    
    @staticmethod
    def validate_success_response(response: APIResponse, expected_fields: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Validate successful API response"""
        if response.status_code not in [200, 201]:
            return False, f"Expected success status code, got {response.status_code}"
        
        if not response.json_data:
            return False, "Expected JSON response"
        
        if expected_fields:
            for field in expected_fields:
                if field not in response.json_data:
                    return False, f"Missing expected field: {field}"
        
        return True, "Valid success response"
    
    @staticmethod
    def validate_error_response(response: APIResponse, expected_status: Optional[int] = None) -> Tuple[bool, str]:
        """Validate error API response"""
        if expected_status and response.status_code != expected_status:
            return False, f"Expected status {expected_status}, got {response.status_code}" 
        
        if response.status_code < 400:
            return False, f"Expected error status code, got {response.status_code}"
        
        return True, "Valid error response"
    
    @staticmethod
    def validate_pagination_response(response: APIResponse) -> Tuple[bool, str]:
        """Validate paginated response structure"""
        is_valid, msg = ResponseValidator.validate_success_response(response)
        if not is_valid:
            return False, msg
        
        data = response.json_data
        required_fields = ['data', 'pagination']
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing pagination field: {field}"
        
        pagination = data['pagination']
        pagination_fields = ['page', 'pageSize', 'totalCount', 'totalPages']
        
        for field in pagination_fields:
            if field not in pagination:
                return False, f"Missing pagination.{field}"
        
        return True, "Valid pagination response"

class TestRunner:
    """Base test runner for individual test modules"""
    
    def __init__(self, name: str, verbose: bool = False, curl: bool = False):
        self.name = name
        self.verbose = verbose
        self.curl = curl
        self.test_count = 0
        self.passed = 0
        self.failed = 0
        self.results: List[TestResult] = []
        
        # Setup curl file if requested (only one mode gets curl output)
        self.curl_file = "tests/curl.sh" if curl else None
    
    def run_test(self, test_name: str, test_func, mode: Optional[TestMode] = None, *args, **kwargs) -> TestResult:
        """Run a single test and track results"""
        self.test_count += 1
        
        mode_suffix = f" ({mode.value})" if mode else ""
        full_name = f"{test_name}{mode_suffix}"
        
        print(f"\n{'='*60}")
        print(f"TEST {self.test_count}: {full_name}")
        print('='*60)
        
        start_time = time.time()
        
        try:
            success = test_func(*args, **kwargs)
            duration = time.time() - start_time
            
            if success:
                print(f"✅ PASS: {full_name} ({duration:.2f}s)")
                self.passed += 1
                result = TestResult(test_name, "PASS", "Test passed", duration, mode)
            else:
                print(f"❌ FAIL: {full_name} ({duration:.2f}s)")
                self.failed += 1
                result = TestResult(test_name, "FAIL", "Test failed", duration, mode)
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ ERROR: {full_name} ({duration:.2f}s)")
            print(f"   Exception: {e}")
            self.failed += 1
            result = TestResult(test_name, "FAIL", f"Exception: {e}", duration, mode)
        
        self.results.append(result)
        return result
    
    def run_4_mode_test(self, test_name: str, test_func, *args, **kwargs) -> List[TestResult]:
        """Run a test across all 4 modes"""
        mode_results = []
        modes = list(TestMode)
        
        for i, mode in enumerate(modes):
            # Only generate curl for first mode to avoid overwriting
            use_curl = self.curl and i == 0
            
            # Create temp config for this mode
            config_file = ConfigManager.create_temp_config(mode)
            
            try:
                # Run test with mode-specific config
                result = self.run_test(
                    test_name, 
                    test_func, 
                    mode, 
                    config_file=config_file,
                    curl=use_curl,
                    *args, 
                    **kwargs
                )
                mode_results.append(result)
                
            finally:
                # Cleanup temp config
                try:
                    Path(config_file).unlink(missing_ok=True)
                except:
                    pass
        
        return mode_results
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY: {self.name}")
        print('='*80)
        print(f"Total tests: {self.test_count}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {(self.passed/self.test_count*100):.1f}%")
        
        if self.failed > 0:
            print("\nFailed tests:")
            for result in self.results:
                if result.status == "FAIL":
                    mode_suffix = f" ({result.mode.value})" if result.mode else ""
                    print(f"  ❌ {result.name}{mode_suffix}: {result.details}")
        
        print('='*80)
        return self.failed == 0

class DatabaseTestHelper:
    """Helper for database-level testing operations"""
    
    @staticmethod
    async def setup_test_data(mode: TestMode):
        """Setup test data for a specific mode"""
        config_file = ConfigManager.create_temp_config(mode)
        
        try:
            # Initialize database connection
            config = Config.initialize(config_file)
            db_type = config.get('database')
            db_uri = config.get('db_uri')
            db_name = config.get('db_name')
            
            await DatabaseFactory.initialize(db_type, db_uri, db_name)
            
            # Insert test accounts
            accounts = TestDataManager.get_test_accounts()
            for account in accounts:
                try:
                    await DatabaseFactory.get_instance().insert("account", account)
                except:
                    pass  # Account might already exist
            
            # Insert test users
            all_users = (
                TestDataManager.get_valid_users() +
                TestDataManager.get_invalid_fk_users() +
                TestDataManager.get_validation_error_users()
            )
            
            for user in all_users:
                try:
                    await DatabaseFactory.get_instance().insert("user", user)
                except:
                    pass  # User might already exist
                    
        finally:
            # Cleanup
            if DatabaseFactory.is_initialized():
                await DatabaseFactory.close()
            Path(config_file).unlink(missing_ok=True)
    
    @staticmethod
    async def cleanup_test_data(mode: TestMode):
        """Cleanup test data for a specific mode"""
        config_file = ConfigManager.create_temp_config(mode)
        
        try:
            # Initialize database connection
            config = Config.initialize(config_file)
            db_type = config.get('database')
            db_uri = config.get('db_uri') 
            db_name = config.get('db_name')
            
            await DatabaseFactory.initialize(db_type, db_uri, db_name)
            
            # Remove test users
            test_user_ids = [
                "valid_all_user_123456",
                "valid_fk_only_user_123456", 
                "bad_fk_user_123456",
                "multiple_errors_user_123456",
                "bad_enum_user_123456",
                "bad_currency_user_123456"
            ]
            
            for user_id in test_user_ids:
                try:
                    await DatabaseFactory.get_instance().delete("user", user_id)
                except:
                    pass
            
            # Remove test accounts
            test_account_ids = [
                "507f1f77bcf86cd799439011",
                "507f1f77bcf86cd799439012"
            ]
            
            for account_id in test_account_ids:
                try:
                    await DatabaseFactory.get_instance().delete("account", account_id)
                except:
                    pass
                    
        finally:
            # Cleanup
            if DatabaseFactory.is_initialized():
                await DatabaseFactory.close()
            Path(config_file).unlink(missing_ok=True)

# Export main classes and functions
__all__ = [
    'TestMode',
    'DatabaseConfig', 
    'TestResult',
    'APIResponse',
    'TestDataManager',
    'ConfigManager',
    'APIClient',
    'ResponseValidator',
    'TestRunner',
    'DatabaseTestHelper'
]