#!/usr/bin/env python3
"""
Optimized Comprehensive Validation Test Matrix

Groups tests by server configuration to minimize restarts.
Tests all combinations systematically with better performance.
"""

import sys
import json
import requests
import subprocess
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

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
class ServerConfig:
    """Server configuration (database + GV setting)"""
    database: Database
    gv_setting: GVSetting
    
    def get_config_data(self) -> dict:
        return {
            "database": self.database.value,
            "db_uri": "mongodb://localhost:27017" if self.database == Database.MONGODB else "http://localhost:9200",
            "db_name": "eventMgr",
            "fk_validation": self.gv_setting.value,
            "unique_validation": self.gv_setting == GVSetting.ON
        }
    
    def __hash__(self):
        return hash((self.database, self.gv_setting))
    
    def __eq__(self, other):
        return isinstance(other, ServerConfig) and self.database == other.database and self.gv_setting == other.gv_setting

@dataclass
class TestCase:
    """Individual test case within a server configuration"""
    name: str
    view_param: ViewParam
    request_type: RequestType
    field_type: FieldType
    
@dataclass
class ValidationExpectation:
    should_have_notifications: bool
    field_errors: List[str]
    description: str

@dataclass 
class TestResult:
    config: ServerConfig
    test_case: TestCase
    expectation: ValidationExpectation
    actual_response: dict
    status_code: int
    success: bool
    error_message: Optional[str] = None
    duration: float = 0.0

class OptimizedValidationTester:
    def __init__(self, server_port: int = 5500):
        self.server_port = server_port
        self.server_process = None
        self.current_config = None
        
        # Test data - using existing user ID
        self.test_user_id = "68814e0e73b517d9e048b093"
    
    def generate_test_matrix(self) -> Dict[ServerConfig, List[TestCase]]:
        """Generate all test cases grouped by server configuration"""
        matrix = defaultdict(list)
        
        # Generate all server configurations
        for db in Database:
            for gv in GVSetting:
                config = ServerConfig(database=db, gv_setting=gv)
                
                # Generate all test cases for this server config
                for view in ViewParam:
                    for req_type in RequestType:
                        for field in FieldType:
                            test_name = f"{view.name}_{req_type.name}_{field.name}"
                            test_case = TestCase(
                                name=test_name,
                                view_param=view,
                                request_type=req_type,
                                field_type=field
                            )
                            matrix[config].append(test_case)
        
        return matrix
    
    def get_validation_expectation(self, config: ServerConfig, test_case: TestCase) -> ValidationExpectation:
        """Define what we expect for each test case"""
        
        if test_case.field_type == FieldType.BAD_FK:
            field_errors = ["accountId"]
            # FK errors only show when GV is ON or VIEW exists
            should_have_notifications = (config.gv_setting == GVSetting.ON or 
                                       test_case.view_param == ViewParam.EXISTS)
            description = "FK validation depends on GV setting or view parameter"
            
        elif test_case.field_type == FieldType.BAD_ENUM:
            field_errors = ["gender"]
            should_have_notifications = True
            description = "Enum validation should always work"
            
        elif test_case.field_type == FieldType.BAD_CURRENCY:
            field_errors = ["netWorth"]
            should_have_notifications = True
            description = "Currency validation should always work"
            
        elif test_case.field_type == FieldType.BAD_BOOLEAN:
            field_errors = ["isAccountOwner"]
            should_have_notifications = True
            description = "Boolean validation should always work"
            
        elif test_case.field_type == FieldType.BAD_STRING:
            field_errors = ["username"]
            should_have_notifications = True
            description = "String validation should always work"
        
        return ValidationExpectation(
            should_have_notifications=should_have_notifications,
            field_errors=field_errors,
            description=description
        )
    
    def build_test_url(self, test_case: TestCase) -> str:
        """Build the API URL for this test case"""
        base_url = f"http://localhost:{self.server_port}/api/user/{self.test_user_id}"
        
        params = []
        
        # Add view parameter if specified
        if test_case.view_param == ViewParam.EXISTS:
            view_data = '{"account":["id"]}'
            import urllib.parse
            view_encoded = urllib.parse.quote(view_data)
            params.append(f"view={view_encoded}")
        
        # Add PFS parameters if specified
        if test_case.request_type == RequestType.PFS:
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
    
    def start_server(self, config: ServerConfig) -> bool:
        """Start server with specific configuration if not already running"""
        if self.current_config == config:
            # Server already running with correct config
            return True
        
        print(f"🚀 Starting server: {config.database.name} + GV={config.gv_setting.name}")
        
        # Stop current server
        self.cleanup_server()
        
        # Create temp config file
        config_data = config.get_config_data()
        config_file = f"temp_matrix_config_{config.database.value}_{config.gv_setting.name}.json"
        
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
            for attempt in range(20):
                try:
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        print(f"  ✅ Server ready (attempt {attempt + 1})")
                        self.current_config = config
                        return True
                except:
                    pass
                time.sleep(1)
            
            print("  ❌ Server failed to start")
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
            except Exception:
                pass
            self.server_process = None
        
        self.current_config = None
        
        # Kill any lingering processes
        try:
            subprocess.run(["pkill", "-f", "main.py"], capture_output=True, text=True)
        except Exception:
            pass
        
        time.sleep(0.5)
        
        # Clean up temp configs
        try:
            for config_file in Path(".").glob("temp_matrix_config_*.json"):
                config_file.unlink()
        except:
            pass
    
    def run_test_case(self, config: ServerConfig, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        expectation = self.get_validation_expectation(config, test_case)
        
        start_time = time.time()
        
        try:
            # Make API request
            test_url = self.build_test_url(test_case)
            
            response = requests.get(test_url, timeout=10)
            response_data = response.json()
            
            # Validate response
            success = self.validate_response(response_data, expectation, test_case)
            
            return TestResult(
                config=config,
                test_case=test_case,
                expectation=expectation,
                actual_response=response_data,
                status_code=response.status_code,
                success=success,
                error_message=None if success else "Response validation failed",
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                config=config,
                test_case=test_case,
                expectation=expectation,
                actual_response={},
                status_code=0,
                success=False,
                error_message=str(e),
                duration=time.time() - start_time
            )
    
    def validate_response(self, response_data: dict, expectation: ValidationExpectation, test_case: TestCase) -> bool:
        """Validate API response matches expectations"""
        
        # Check if notifications exist
        has_notifications = (
            'notifications' in response_data and 
            response_data['notifications'] is not None and
            len(response_data.get('notifications', [])) > 0
        )
        
        if expectation.should_have_notifications and not has_notifications:
            return False
        
        if not expectation.should_have_notifications and has_notifications:
            return False
        
        if has_notifications and expectation.field_errors:
            notifications = response_data.get('notifications', [])
            validation_notifications = [n for n in notifications if n.get('type') == 'VALIDATION']
            
            # Check for expected field errors
            for expected_field in expectation.field_errors:
                field_notifications = [n for n in validation_notifications 
                                     if n.get('field_name') == expected_field]
                if not field_notifications:
                    return False
        
        return True
    
    def run_focused_tests(self) -> List[TestResult]:
        """Run a focused set of tests for debugging"""
        
        # Test just MongoDB with key scenarios
        mongo_config = ServerConfig(Database.MONGODB, GVSetting.OFF)
        
        focus_cases = [
            TestCase("currency_normal", ViewParam.MISSING, RequestType.NORMAL, FieldType.BAD_CURRENCY),
            TestCase("enum_normal", ViewParam.MISSING, RequestType.NORMAL, FieldType.BAD_ENUM),
            TestCase("fk_normal", ViewParam.MISSING, RequestType.NORMAL, FieldType.BAD_FK),
        ]
        
        results = []
        
        print("🎯 FOCUSED VALIDATION TEST")
        print("=" * 60)
        
        # Start server once
        if not self.start_server(mongo_config):
            print("❌ Failed to start server")
            return []
        
        try:
            for i, test_case in enumerate(focus_cases, 1):
                print(f"\n[{i}/{len(focus_cases)}] Testing: {test_case.name}")
                print(f"   Field type: {test_case.field_type.name}")
                print(f"   URL: {self.build_test_url(test_case)}")
                
                result = self.run_test_case(mongo_config, test_case)
                results.append(result)
                
                # Show immediate result
                status = "✅ PASS" if result.success else "❌ FAIL"
                print(f"   {status} ({result.duration:.1f}s)")
                
                if not result.success:
                    print(f"   Error: {result.error_message}")
                    
        finally:
            self.cleanup_server()
        
        return results
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all test scenarios grouped by server configuration"""
        matrix = self.generate_test_matrix()
        all_results = []
        
        print("🧪 COMPREHENSIVE VALIDATION TEST MATRIX")
        print("=" * 80)
        print(f"Testing {sum(len(cases) for cases in matrix.values())} scenarios across {len(matrix)} server configurations")
        print()
        
        config_num = 0
        total_configs = len(matrix)
        
        for config, test_cases in matrix.items():
            config_num += 1
            print(f"\n[{config_num}/{total_configs}] Server Config: {config.database.name} + GV={config.gv_setting.name}")
            print(f"Running {len(test_cases)} test cases...")
            
            # Start server for this configuration
            if not self.start_server(config):
                print(f"❌ Failed to start server for {config.database.name}")
                # Mark all test cases as failed
                for test_case in test_cases:
                    expectation = self.get_validation_expectation(config, test_case)
                    result = TestResult(
                        config=config,
                        test_case=test_case,
                        expectation=expectation,
                        actual_response={},
                        status_code=0,
                        success=False,
                        error_message="Server failed to start"
                    )
                    all_results.append(result)
                continue
            
            # Run all test cases for this configuration
            config_results = []
            for i, test_case in enumerate(test_cases, 1):
                print(f"  [{i}/{len(test_cases)}] {test_case.name}: ", end="", flush=True)
                
                result = self.run_test_case(config, test_case)
                config_results.append(result)
                all_results.append(result)
                
                # Show immediate result
                status = "PASS" if result.success else "FAIL"
                print(f"{status} ({result.duration:.1f}s)")
            
            # Show config summary
            passed = sum(1 for r in config_results if r.success)
            print(f"  Config summary: {passed}/{len(config_results)} passed")
        
        # Clean up final server
        self.cleanup_server()
        
        return all_results
    
    def print_results_summary(self, results: List[TestResult]):
        """Print comprehensive test summary"""
        print(f"\n{'='*80}")
        print("VALIDATION TEST MATRIX RESULTS")
        print('='*80)
        
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed
        
        print(f"Total test cases: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(passed/total)*100:.1f}%")
        print()
        
        # Group results by categories
        by_database = defaultdict(lambda: {"passed": 0, "total": 0})
        by_field_type = defaultdict(lambda: {"passed": 0, "total": 0})
        by_gv_setting = defaultdict(lambda: {"passed": 0, "total": 0})
        
        for result in results:
            # By database
            db = result.config.database.name
            by_database[db]["total"] += 1
            if result.success:
                by_database[db]["passed"] += 1
            
            # By field type
            field = result.test_case.field_type.name
            by_field_type[field]["total"] += 1
            if result.success:
                by_field_type[field]["passed"] += 1
            
            # By GV setting
            gv = result.config.gv_setting.name
            by_gv_setting[gv]["total"] += 1
            if result.success:
                by_gv_setting[gv]["passed"] += 1
        
        print("Results by Database:")
        for db, stats in sorted(by_database.items()):
            print(f"  {db}: {stats['passed']}/{stats['total']} ({(stats['passed']/stats['total'])*100:.1f}%)")
        
        print("\nResults by Field Type:")
        for field, stats in sorted(by_field_type.items()):
            print(f"  {field}: {stats['passed']}/{stats['total']} ({(stats['passed']/stats['total'])*100:.1f}%)")
        
        print("\nResults by GV Setting:")
        for gv, stats in sorted(by_gv_setting.items()):
            print(f"  {gv}: {stats['passed']}/{stats['total']} ({(stats['passed']/stats['total'])*100:.1f}%)")
        
        # Show failed scenarios
        failed_results = [r for r in results if not r.success]
        if failed_results:
            print(f"\nFailed Test Cases:")
            for result in failed_results:
                config_name = f"{result.config.database.name}_{result.config.gv_setting.name}"
                print(f"  ❌ {config_name}_{result.test_case.name}: {result.error_message}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Optimized Validation Test Matrix')
    parser.add_argument('--focused', action='store_true',
                       help='Run focused test set for debugging (3 scenarios)')
    parser.add_argument('--all', action='store_true',
                       help='Run all 80 test scenarios')
    args = parser.parse_args()
    
    tester = OptimizedValidationTester()
    
    try:
        if args.focused:
            print("🎯 Running focused test set...")
            results = tester.run_focused_tests()
        elif args.all:
            print("🌍 Running all 80 test scenarios...")
            results = tester.run_all_tests()
        else:
            print("🎯 Running focused test set by default (use --all for complete matrix)...")
            results = tester.run_focused_tests()
        
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