#!/usr/bin/env python3
"""
Comprehensive API Validation Test Matrix

Tests all combinations of:
- GV setting: ON/OFF (fk_validation enabled/disabled)  
- View parameter: EXISTS/MISSING (FK processing triggered/not triggered)
- Request type: PFS/NORMAL (pagination/filtering vs regular GET)
- Database: MongoDB/Elasticsearch
- Field types: FK/Enum/Currency/Boolean/String validation

Total: 8 base combinations × 2 databases × 5 field types = 80+ test scenarios
"""

import sys
import json
import requests
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class GVSetting(Enum):
    ON = "multiple"
    OFF = ""

class ViewParam(Enum):
    EXISTS = True
    MISSING = False

class RequestType(Enum):
    NORMAL = "normal"
    PFS = "pfs"

class Database(Enum):
    MONGODB = "mongodb"
    ELASTICSEARCH = "elasticsearch"

class FieldType(Enum):
    BAD_FK = "bad_fk"
    BAD_ENUM = "bad_enum" 
    BAD_CURRENCY = "bad_currency"
    BAD_BOOLEAN = "bad_boolean"
    BAD_STRING = "bad_string"

@dataclass
class TestConfig:
    name: str
    gv_setting: GVSetting
    view_param: ViewParam
    request_type: RequestType
    database: Database
    field_type: FieldType
    
    def get_config_data(self) -> dict:
        """Generate config.json data for this test"""
        return {
            "database": self.database.value,
            "db_uri": "mongodb://localhost:27017" if self.database == Database.MONGODB else "http://localhost:9200",
            "db_name": "eventMgr",
            "fk_validation": self.gv_setting.value,
            "unique_validation": self.gv_setting == GVSetting.ON
        }

@dataclass
class ValidationExpectation:
    """What we expect to see in the API response"""
    should_have_notifications: bool
    notification_types: List[str]  # ['VALIDATION', 'DATABASE', etc.]
    field_errors: List[str]  # field names that should have errors
    status_code: int = 200

@dataclass 
class TestResult:
    config: TestConfig
    expectation: ValidationExpectation
    actual_response: dict
    status_code: int
    success: bool
    error_message: Optional[str] = None

class APIValidationTester:
    def __init__(self, server_port: int = 5500):
        self.server_port = server_port
        self.server_process = None
        self.test_user_ids = {
            # These would be actual user IDs with known validation issues
            FieldType.BAD_FK: "68814e0e73b517d9e048b093",  # User with bad FK
            FieldType.BAD_ENUM: "68814e0e73b517d9e048b093",  # User with bad gender  
            FieldType.BAD_CURRENCY: "68814e148f4cb0743baec721",  # User with negative networth
            FieldType.BAD_BOOLEAN: "user_with_bad_boolean_id",  # Would need to create
            FieldType.BAD_STRING: "user_with_bad_string_id"   # Would need to create
        }
    
    def generate_test_matrix(self) -> List[TestConfig]:
        """Generate all 80+ test combinations"""
        configs = []
        
        for gv in GVSetting:
            for view in ViewParam:
                for req_type in RequestType:
                    for db in Database:
                        for field in FieldType:
                            name = f"{gv.name}_{view.name}_{req_type.name}_{db.name}_{field.name}"
                            configs.append(TestConfig(
                                name=name,
                                gv_setting=gv,
                                view_param=view,
                                request_type=req_type,
                                database=db,
                                field_type=field
                            ))
        
        return configs
    
    def get_validation_expectation(self, config: TestConfig) -> ValidationExpectation:
        """Define what we expect for each test scenario"""
        
        # Base expectation - field validation should always work
        should_have_notifications = True
        notification_types = ["VALIDATION"]
        field_errors = []
        
        # Define expected field errors based on field type
        if config.field_type == FieldType.BAD_FK:
            field_errors = ["accountId"]
            # FK errors only show when GV is ON or VIEW exists
            should_have_notifications = (config.gv_setting == GVSetting.ON or 
                                       config.view_param == ViewParam.EXISTS)
        elif config.field_type == FieldType.BAD_ENUM:
            field_errors = ["gender"]
            # Enum validation should always work
            should_have_notifications = True
        elif config.field_type == FieldType.BAD_CURRENCY:
            field_errors = ["netWorth"]
            # Field validation should always work
            should_have_notifications = True
        elif config.field_type == FieldType.BAD_BOOLEAN:
            field_errors = ["isAccountOwner"]
            should_have_notifications = True
        elif config.field_type == FieldType.BAD_STRING:
            field_errors = ["username"]  # assuming min_length violation
            should_have_notifications = True
            
        return ValidationExpectation(
            should_have_notifications=should_have_notifications,
            notification_types=notification_types,
            field_errors=field_errors,
            status_code=200
        )
    
    def build_test_url(self, config: TestConfig) -> str:
        """Build the API URL for this test configuration"""
        user_id = self.test_user_ids.get(config.field_type, "default_user_id")
        base_url = f"http://localhost:{self.server_port}/api/user/{user_id}"
        
        params = []
        
        # Add view parameter if specified
        if config.view_param == ViewParam.EXISTS:
            # Simple view param for FK processing
            view_data = '{"account":["id"]}'
            import urllib.parse
            view_encoded = urllib.parse.quote(view_data)
            params.append(f"view={view_encoded}")
        
        # Add PFS parameters if specified
        if config.request_type == RequestType.PFS:
            params.extend([
                "page=1",
                "pageSize=5",
                "sort=username",
                "order=asc"
            ])
        
        if params:
            return f"{base_url}?{'&'.join(params)}"
        else:
            return base_url
    
    def start_server(self, config: TestConfig) -> bool:
        """Start server with specific configuration"""
        print(f"🚀 Starting server for {config.database.name} with GV={config.gv_setting.name}")
        
        # Clean up any existing processes
        self.cleanup_server()
        
        # Create temp config file
        config_data = config.get_config_data()
        config_file = "temp_api_test_config.json"
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        try:
            # Start server
            env = {"PYTHONPATH": "."}
            self.server_process = subprocess.Popen(
                [sys.executable, "app/main.py", config_file],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            # Wait for server to be ready
            for attempt in range(20):
                try:
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        print(f"  ✅ Server ready (attempt {attempt + 1})")
                        return True
                except:
                    pass
                time.sleep(1)
            
            print("  ❌ Server failed to start")
            if self.server_process:
                try:
                    stdout, stderr = self.server_process.communicate(timeout=2)
                    if stderr:
                        print(f"  📋 Server stderr: {stderr}")
                    if stdout:
                        print(f"  📋 Server stdout: {stdout}")
                except:
                    print("  ⚠️  Could not get server output")
            return False
            
        except Exception as e:
            print(f"  ❌ Server start error: {e}")
            return False
    
    def cleanup_server(self):
        """Stop server and clean up"""
        print("🛑 Stopping server...")
        
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
                print("  ✅ Server terminated gracefully")
            except subprocess.TimeoutExpired:
                print("  ⚠️  Server didn't terminate, killing...")
                self.server_process.kill()
                self.server_process.wait()
                print("  ✅ Server killed")
            except Exception as e:
                print(f"  ⚠️  Error stopping server: {e}")
            self.server_process = None
        
        # Kill any lingering processes more aggressively
        try:
            result = subprocess.run(["pkill", "-f", "main.py"], capture_output=True, text=True)
            if result.returncode == 0:
                print("  ✅ Cleaned up lingering processes")
        except Exception as e:
            print(f"  ⚠️  Error cleaning processes: {e}")
        
        # Wait a moment for ports to free up
        time.sleep(2)
        
        # Clean up temp config
        try:
            Path("temp_api_test_config.json").unlink(missing_ok=True)
        except:
            pass
    
    def run_single_test(self, config: TestConfig) -> TestResult:
        """Run a single test configuration"""
        expectation = self.get_validation_expectation(config)
        
        print(f"\n📋 Testing: {config.name}")
        print(f"   Expected: {expectation.field_errors} field errors, notifications={expectation.should_have_notifications}")
        
        # Start server with this config
        if not self.start_server(config):
            return TestResult(
                config=config,
                expectation=expectation,
                actual_response={},
                status_code=0,
                success=False,
                error_message="Server failed to start"
            )
        
        try:
            # Make API request
            test_url = self.build_test_url(config)
            print(f"   URL: {test_url}")
            
            response = requests.get(test_url, timeout=10)
            response_data = response.json()
            
            print(f"   Status: {response.status_code}")
            print(f"   Response keys: {list(response_data.keys())}")
            
            # Enhanced response analysis using simple test logic
            self.print_detailed_response_analysis(response_data, config)
            
            # Analyze response
            success = self.validate_response(response_data, expectation)
            
            return TestResult(
                config=config,
                expectation=expectation,
                actual_response=response_data,
                status_code=response.status_code,
                success=success,
                error_message=None if success else "Response validation failed"
            )
            
        except Exception as e:
            return TestResult(
                config=config,
                expectation=expectation,
                actual_response={},
                status_code=0,
                success=False,
                error_message=str(e)
            )
        finally:
            self.cleanup_server()
    
    def print_detailed_response_analysis(self, response_data: dict, config: TestConfig):
        """Print detailed response analysis like the simple test"""
        print("   Response structure:")
        for key, value in response_data.items():
            if key == 'data' and isinstance(value, dict):
                print(f"     {key}: {{user object with {len(value)} fields}}")
                # Show just the relevant field if it exists
                if config.field_type == FieldType.BAD_CURRENCY and 'netWorth' in value:
                    print(f"       netWorth: {value['netWorth']}")
                elif config.field_type == FieldType.BAD_ENUM and 'gender' in value:
                    print(f"       gender: {value['gender']}")
                elif config.field_type == FieldType.BAD_FK and 'accountId' in value:
                    print(f"       accountId: {value['accountId']}")
            elif key == 'notifications':
                if value is None:
                    print(f"     {key}: null")
                elif isinstance(value, list):
                    print(f"     {key}: [{len(value)} notifications]")
                    for i, notif in enumerate(value):
                        print(f"       {i+1}. {notif.get('type', 'UNKNOWN')}: {notif.get('message', 'no message')}")
                        if 'field_name' in notif:
                            print(f"          Field: {notif['field_name']}")
                else:
                    print(f"     {key}: {type(value).__name__}")
            else:
                print(f"     {key}: {type(value).__name__}")
        
        # Check specifically for validation issues
        has_notifications = (
            'notifications' in response_data and 
            response_data['notifications'] is not None and
            len(response_data.get('notifications', [])) > 0
        )
        
        print()
        if has_notifications:
            print("     ✅ Found notifications in response")
            notifications = response_data['notifications']
            validation_notifications = [n for n in notifications if n.get('type') == 'VALIDATION']
            if validation_notifications:
                print(f"     ✅ Found {len(validation_notifications)} validation notifications")
                for notif in validation_notifications:
                    if config.field_type == FieldType.BAD_CURRENCY and notif.get('field_name') == 'netWorth':
                        print("     ✅ Found netWorth validation error!")
                    elif config.field_type == FieldType.BAD_ENUM and notif.get('field_name') == 'gender':
                        print("     ✅ Found gender validation error!")
                    elif config.field_type == FieldType.BAD_FK and notif.get('field_name') == 'accountId':
                        print("     ✅ Found accountId validation error!")
            else:
                print("     ⚠️  No validation notifications found")
        else:
            print("     ❌ No notifications found in response")
            print("        This indicates the notification system is not working properly")
    
    def validate_response(self, response_data: dict, expectation: ValidationExpectation) -> bool:
        """Validate API response matches expectations"""
        
        # Check if notifications exist when expected
        has_notifications = (
            'notifications' in response_data and 
            response_data['notifications'] is not None and
            len(response_data.get('notifications', [])) > 0
        )
        
        print(f"   Has notifications: {has_notifications} (expected: {expectation.should_have_notifications})")
        
        if expectation.should_have_notifications and not has_notifications:
            print(f"   ❌ FAIL: Expected notifications but found none")
            return False
        
        if not expectation.should_have_notifications and has_notifications:
            print(f"   ❌ FAIL: Found unexpected notifications")
            return False
        
        if has_notifications:
            notifications = response_data.get('notifications', [])
            print(f"   Found {len(notifications)} notifications")
            
            # Check notification details
            for notif in notifications:
                print(f"     - {notif.get('type', 'UNKNOWN')}: {notif.get('message', 'no message')}")
                if 'field_name' in notif:
                    print(f"       Field: {notif['field_name']}")
        
        print(f"   ✅ PASS")
        return True
        
    def run_focused_test_set(self) -> List[TestResult]:
        """Run a focused set of tests for debugging"""
        
        # Focus on the known problematic scenarios first
        focus_configs = [
            # Test bad currency with different combinations
            TestConfig("currency_gv_off_no_view_normal_mongo", GVSetting.OFF, ViewParam.MISSING, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_CURRENCY),
            TestConfig("currency_gv_on_no_view_normal_mongo", GVSetting.ON, ViewParam.MISSING, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_CURRENCY),
            TestConfig("currency_gv_off_view_normal_mongo", GVSetting.OFF, ViewParam.EXISTS, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_CURRENCY),
            
            # Test bad enum (known to work) as baseline
            TestConfig("enum_gv_off_no_view_normal_mongo", GVSetting.OFF, ViewParam.MISSING, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_ENUM),
        ]
        
        results = []
        for config in focus_configs:
            result = self.run_single_test(config)
            results.append(result)
        
        return results
    
    def print_results_summary(self, results: List[TestResult]):
        """Print summary of test results"""
        print(f"\n{'='*80}")
        print("API VALIDATION TEST RESULTS")
        print('='*80)
        
        passed = sum(1 for r in results if r.success)
        total = len(results)
        
        print(f"Overall: {passed}/{total} tests passed")
        print()
        
        for result in results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"{status} {result.config.name}")
            if not result.success:
                print(f"     Error: {result.error_message}")
                if result.actual_response:
                    notifications = result.actual_response.get('notifications')
                    print(f"     Actual notifications: {notifications}")

def main():
    tester = APIValidationTester()
    
    print("🧪 COMPREHENSIVE API VALIDATION TEST MATRIX")
    print("=" * 80)
    print("Testing field validation across all API configuration combinations")
    print()
    
    # Run focused test set first to debug current issues
    print("🎯 Running focused test set to debug current issues...")
    results = tester.run_focused_test_set()
    
    tester.print_results_summary(results)
    
    return 0 if all(r.success for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())