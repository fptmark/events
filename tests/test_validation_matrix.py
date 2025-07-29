#!/usr/bin/env python3
"""
Comprehensive Validation Test Matrix

Tests all combinations of:
- GV setting: ON/OFF (get_validation enabled/disabled)  
- View parameter: EXISTS/MISSING (FK processing triggered/not triggered)
- Request type: PFS/NORMAL (pagination/filtering vs regular GET)
- Database: MongoDB/Elasticsearch
- Field types: FK/Enum/Currency/Boolean/String validation

Total: 2 GV × 2 View × 2 Request × 2 Database × 5 Field = 80 test scenarios
"""

import sys
import json
import requests
import subprocess
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class GVSetting(Enum):
    ON = "get_all"
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
class TestScenario:
    """Single test scenario configuration"""
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
            "get_validation": self.gv_setting.value,
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
    scenario: TestScenario
    expectation: ValidationExpectation
    actual_response: dict
    status_code: int
    success: bool
    error_message: Optional[str] = None
    duration: float = 0.0

class ValidationMatrixTester:
    def __init__(self, server_port: int = 5500):
        self.server_port = server_port
        self.server_process = None
        
        # Test data - all using the same user ID that exists
        self.test_user_id = "68814e0e73b517d9e048b093"
    
    def generate_test_matrix(self) -> List[TestScenario]:
        """Generate all 80 test scenarios"""
        scenarios = []
        
        for gv in GVSetting:
            for view in ViewParam:
                for req_type in RequestType:
                    for db in Database:
                        for field in FieldType:
                            name = f"{gv.name}_{view.name}_{req_type.name}_{db.name}_{field.name}"
                            scenarios.append(TestScenario(
                                name=name,
                                gv_setting=gv,
                                view_param=view,
                                request_type=req_type,
                                database=db,
                                field_type=field
                            ))
        
        return scenarios
    
    def get_validation_expectation(self, scenario: TestScenario) -> ValidationExpectation:
        """Define what we expect for each test scenario"""
        
        # Base expectation - field validation should always work for most cases
        should_have_notifications = True
        notification_types = ["VALIDATION"]
        field_errors = []
        
        # Define expected field errors based on field type
        if scenario.field_type == FieldType.BAD_FK:
            field_errors = ["accountId"]
            # FK errors only show when GV is ON or VIEW exists
            should_have_notifications = (scenario.gv_setting == GVSetting.ON or 
                                       scenario.view_param == ViewParam.EXISTS)
        elif scenario.field_type == FieldType.BAD_ENUM:
            field_errors = ["gender"]
            # Enum validation should always work
            should_have_notifications = True
        elif scenario.field_type == FieldType.BAD_CURRENCY:
            field_errors = ["netWorth"]
            # Field validation should always work
            should_have_notifications = True
        elif scenario.field_type == FieldType.BAD_BOOLEAN:
            field_errors = ["isAccountOwner"]
            should_have_notifications = True
        elif scenario.field_type == FieldType.BAD_STRING:
            field_errors = ["username"]  # assuming min_length violation
            should_have_notifications = True
            
        return ValidationExpectation(
            should_have_notifications=should_have_notifications,
            notification_types=notification_types,
            field_errors=field_errors,
            status_code=200
        )
    
    def build_test_url(self, scenario: TestScenario) -> str:
        """Build the API URL for this test scenario"""
        base_url = f"http://localhost:{self.server_port}/api/user/{self.test_user_id}"
        
        params = []
        
        # Add view parameter if specified
        if scenario.view_param == ViewParam.EXISTS:
            # Simple view param for FK processing
            view_data = '{"account":["id"]}'
            import urllib.parse
            view_encoded = urllib.parse.quote(view_data)
            params.append(f"view={view_encoded}")
        
        # Add PFS parameters if specified
        if scenario.request_type == RequestType.PFS:
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
    
    def start_server(self, scenario: TestScenario) -> bool:
        """Start server with specific configuration"""
        print(f"🚀 Starting server for {scenario.database.name} with GV={scenario.gv_setting.name}")
        
        # Clean up any existing processes
        self.cleanup_server()
        
        # Create temp config file
        config_data = scenario.get_config_data()
        config_file = f"temp_matrix_test_config_{scenario.database.value}_{scenario.gv_setting.name}.json"
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        try:
            # Start server
            env = os.environ.copy()
            env["PYTHONPATH"] = "."
            
            self.server_process = subprocess.Popen(
                [sys.executable, "app/main.py", config_file],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            # Wait for server to be ready
            for attempt in range(30):
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
                except:
                    print("  ⚠️  Could not get server output")
            return False
            
        except Exception as e:
            print(f"  ❌ Server start error: {e}")
            return False
    
    def cleanup_server(self):
        """Stop server and clean up"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
            except Exception as e:
                print(f"  ⚠️  Error stopping server: {e}")
            self.server_process = None
        
        # Kill any lingering processes
        try:
            subprocess.run(["pkill", "-f", "main.py"], capture_output=True, text=True)
        except Exception:
            pass
        
        # Wait for ports to free up
        time.sleep(1)
        
        # Clean up temp configs
        try:
            for config_file in Path(".").glob("temp_matrix_test_config_*.json"):
                config_file.unlink()
        except:
            pass
    
    def run_single_test(self, scenario: TestScenario) -> TestResult:
        """Run a single test scenario"""
        expectation = self.get_validation_expectation(scenario)
        
        print(f"\n📋 Testing: {scenario.name}")
        print(f"   Expected: {expectation.field_errors} field errors, notifications={expectation.should_have_notifications}")
        
        start_time = time.time()
        
        # Start server with this config
        if not self.start_server(scenario):
            return TestResult(
                scenario=scenario,
                expectation=expectation,
                actual_response={},
                status_code=0,
                success=False,
                error_message="Server failed to start",
                duration=time.time() - start_time
            )
        
        try:
            # Make API request
            test_url = self.build_test_url(scenario)
            print(f"   URL: {test_url}")
            
            response = requests.get(test_url, timeout=10)
            response_data = response.json()
            
            print(f"   Status: {response.status_code}")
            
            # Analyze response using the validation completeness logic
            success = self.validate_response(response_data, expectation, scenario)
            
            return TestResult(
                scenario=scenario,
                expectation=expectation,
                actual_response=response_data,
                status_code=response.status_code,
                success=success,
                error_message=None if success else "Response validation failed",
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                scenario=scenario,
                expectation=expectation,
                actual_response={},
                status_code=0,
                success=False,
                error_message=str(e),
                duration=time.time() - start_time
            )
        finally:
            self.cleanup_server()
    
    def validate_response(self, response_data: dict, expectation: ValidationExpectation, scenario: TestScenario) -> bool:
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
            
            # Check for expected field errors
            validation_notifications = [n for n in notifications if n.get('type') == 'VALIDATION']
            
            if expectation.field_errors:
                for expected_field in expectation.field_errors:
                    field_notifications = [n for n in validation_notifications 
                                         if n.get('field_name') == expected_field]
                    if not field_notifications:
                        print(f"   ❌ FAIL: No validation errors found for expected field '{expected_field}'")
                        return False
                    else:
                        print(f"   ✅ Found validation error for {expected_field}: {field_notifications[0].get('message', 'N/A')}")
        
        print(f"   ✅ PASS")
        return True
    
    def run_focused_test_set(self) -> List[TestResult]:
        """Run a focused set of tests for debugging current issues"""
        
        # Focus on the scenarios we know should work vs fail
        focus_scenarios = [
            # Test currency validation (known issue from logs)
            TestScenario("currency_mongo_gv_off", GVSetting.OFF, ViewParam.MISSING, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_CURRENCY),
            TestScenario("currency_mongo_gv_on", GVSetting.ON, ViewParam.MISSING, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_CURRENCY),
            
            # Test enum validation (should work)
            TestScenario("enum_mongo_gv_off", GVSetting.OFF, ViewParam.MISSING, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_ENUM),
            
            # Test FK validation (depends on GV setting)
            TestScenario("fk_mongo_gv_off", GVSetting.OFF, ViewParam.MISSING, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_FK),
            TestScenario("fk_mongo_gv_on", GVSetting.ON, ViewParam.MISSING, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_FK),
            
            # Test with view parameter
            TestScenario("fk_mongo_gv_off_view", GVSetting.OFF, ViewParam.EXISTS, RequestType.NORMAL, Database.MONGODB, FieldType.BAD_FK),
        ]
        
        results = []
        for scenario in focus_scenarios:
            result = self.run_single_test(scenario)
            results.append(result)
        
        return results
    
    def run_all_scenarios(self) -> List[TestResult]:
        """Run all 80 test scenarios"""
        scenarios = self.generate_test_matrix()
        results = []
        
        print("🧪 COMPREHENSIVE VALIDATION TEST MATRIX")
        print("=" * 80)
        print(f"Running {len(scenarios)} test scenarios...")
        print()
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n[{i}/{len(scenarios)}] Running scenario: {scenario.name}")
            result = self.run_single_test(scenario)
            results.append(result)
            
            # Print immediate result
            if result.success:
                print(f"✅ {scenario.name}: PASS ({result.duration:.1f}s)")
            else:
                print(f"❌ {scenario.name}: FAIL - {result.error_message} ({result.duration:.1f}s)")
        
        return results
    
    def print_results_summary(self, results: List[TestResult]):
        """Print comprehensive test summary"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE VALIDATION TEST MATRIX RESULTS")
        print('='*80)
        
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed
        
        print(f"Total scenarios: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        print()
        
        # Group results by categories
        by_database = {}
        by_field_type = {}
        by_gv_setting = {}
        
        for result in results:
            # By database
            db = result.scenario.database.name
            if db not in by_database:
                by_database[db] = {"passed": 0, "total": 0}
            by_database[db]["total"] += 1
            if result.success:
                by_database[db]["passed"] += 1
            
            # By field type
            field = result.scenario.field_type.name
            if field not in by_field_type:
                by_field_type[field] = {"passed": 0, "total": 0}
            by_field_type[field]["total"] += 1
            if result.success:
                by_field_type[field]["passed"] += 1
            
            # By GV setting
            gv = result.scenario.gv_setting.name
            if gv not in by_gv_setting:
                by_gv_setting[gv] = {"passed": 0, "total": 0}
            by_gv_setting[gv]["total"] += 1
            if result.success:
                by_gv_setting[gv]["passed"] += 1
        
        print("Results by Database:")
        for db, stats in by_database.items():
            print(f"  {db}: {stats['passed']}/{stats['total']} ({(stats['passed']/stats['total'])*100:.1f}%)")
        
        print("\nResults by Field Type:")
        for field, stats in by_field_type.items():
            print(f"  {field}: {stats['passed']}/{stats['total']} ({(stats['passed']/stats['total'])*100:.1f}%)")
        
        print("\nResults by GV Setting:")
        for gv, stats in by_gv_setting.items():
            print(f"  {gv}: {stats['passed']}/{stats['total']} ({(stats['passed']/stats['total'])*100:.1f}%)")
        
        # Show failed scenarios
        failed_results = [r for r in results if not r.success]
        if failed_results:
            print(f"\nFailed Scenarios:")
            for result in failed_results:
                print(f"  ❌ {result.scenario.name}: {result.error_message}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Comprehensive Validation Test Matrix')
    parser.add_argument('--focused', action='store_true',
                       help='Run focused test set for debugging (6 scenarios)')
    parser.add_argument('--all', action='store_true',
                       help='Run all 80 test scenarios')
    args = parser.parse_args()
    
    tester = ValidationMatrixTester()
    
    try:
        if args.focused:
            print("🎯 Running focused test set for debugging...")
            results = tester.run_focused_test_set()
        elif args.all:
            print("🌍 Running all 80 test scenarios...")
            results = tester.run_all_scenarios()
        else:
            print("🎯 Running focused test set by default (use --all for complete matrix)...")
            results = tester.run_focused_test_set()
        
        tester.print_results_summary(results)
        
        # Return exit code based on overall success
        all_successful = all(r.success for r in results)
        return 0 if all_successful else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test runner failed: {e}")
        return 1
    finally:
        tester.cleanup_server()

if __name__ == "__main__":
    sys.exit(main())