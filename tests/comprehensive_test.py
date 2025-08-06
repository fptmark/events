#!/usr/bin/env python3
"""
Comprehensive test runner that orchestrates all test files across 4 modes.
Supports server lifecycle management, data creation, and multiple test modes.
"""

import sys
import os
import subprocess
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import BaseTestFramework
from tests.test_basic import BasicAPITester
from tests.test_view import ViewParameterTester
from tests.test_pagination import PaginationTester
from tests.test_sorting import SortingTester
from tests.test_filtering import FilteringTester
from tests.test_combinations import CombinationTester
from tests.random_data import RandomData
from tests.curl import CurlManager
from tests.test_case import TestCase


@dataclass
class TestConfig:
    name: str
    database: str 
    config_data: dict

@dataclass
class TestResult:
    config_name: str
    success: bool
    passed: int
    failed: int
    total: int
    duration: float
    error: Optional[str] = None

class ComprehensiveTestRunner:
    """Comprehensive test runner with server lifecycle and data management"""
    
    def __init__(self, verbose: bool = False, dbs: List[str] = [], configurations: List[TestConfig] = [],
                 connection: bool = False, newdata: bool = False, test_cases: Dict[str, Tuple[str, type]] = {}, entity: str = "user",
                 request_delay: float = 0.0, config_file = None):
        self.server_port = 5500
        self.server_process = None
        self.verbose = verbose
        self.config_file = config_file  # Optional config file for curl generation
        
        self.dbs = dbs
        self.connection = connection
        self.newdata = newdata
        self.configurations = configurations
        self.test_cases = test_cases 
        self.entity = entity
        self.request_delay = request_delay
    
        
    def cleanup_port(self):
        """Kill any processes using our port"""
        try:
            subprocess.run(["pkill", "-f", "main.py"], check=False)
            time.sleep(1)
        except:
            pass
    
    def start_server(self, config_file: str) -> bool:
        """Start server with given config file"""
        self.cleanup_port()
        if self.verbose:
            print(f"🚀 Starting server with {config_file}")
        else:
            print(f"🚀 Starting server...")
        
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = '.'
            
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
                    import requests
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        if self.verbose:
                            print(f"  ✅ Server ready (attempt {attempt + 1})")
                        return True
                except:
                    pass
                time.sleep(1)
            
            print("  ❌ Server failed to start")
            return False
            
        except Exception as e:
            print(f"  ❌ Server start error: {e}")
            return False
    
    def stop_server(self):
        """Stop the server"""
        if self.verbose:
            print("🛑 Stopping server")
        if self.server_process:
            try:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                    self.server_process.wait()
            except:
                pass
            self.server_process = None
        self.cleanup_port()
        time.sleep(1)
    
    def create_config_file(self, config: TestConfig) -> str:
        """Create temporary config file"""
        filename = "tests/temp_test_config.json"
        with open(filename, 'w') as f:
            json.dump(config.config_data, f, indent=2)
        return filename
    
    async def create_test_data(self, config_file: str) -> bool:
        """Create test data using test_data_setup.py"""
        if self.verbose:
            print("  🧹 Wiping existing data and creating fresh test data...")
        
        try:
            # Get metadata using requests instead of undefined get_curl
            import requests
            response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=10)
            if response.status_code != 200:
                raise Exception(f"Failed to fetch metadata: {response.status_code}")
            metadata = response.text
            
            create = RandomData(metadata, self.entity)
            valid, invalid = create.generate_records(good_count=50, bad_count=20)
            
            # Save generated records to database
            if self.verbose:
                print(f"  📝 Generated {len(valid)} valid and {len(invalid)} invalid records")
            
            # Save all generated records (includes both random + known test users)
            success = await self._save_generated_records_to_database(config_file, valid, invalid)
            
            if success:
                if self.verbose:
                    print("  ✅ Test data created successfully (random + known test users)")
                return True
            else:
                print("  ❌ Test data creation failed")
                return False
                
        except Exception as e:
            print(f"  ❌ Test data creation error: {e}")
            return False
    
    async def _save_generated_records_to_database(self, config_file: str, valid_records: List[Dict], invalid_records: List[Dict]) -> bool:
        """Save generated records directly to database using DatabaseFactory"""
        try:
            # Import required modules
            from app.config import Config
            from app.db import DatabaseFactory
            from datetime import datetime, timezone
            import uuid
            
            # Initialize database connection
            config = Config.initialize(config_file)
            db_type: str = config.get('database', '')
            db_uri: str = config.get('db_uri', '')
            db_name: str = config.get('db_name', '')
            
            await DatabaseFactory.initialize(db_type, db_uri, db_name)
            
            saved_valid = 0
            saved_invalid = 0
            
            # Save valid records
            for i, record in enumerate(valid_records):
                try:
                    # Ensure required fields
                    if 'id' not in record:
                        record['id'] = f"generated_valid_{i+1}_{uuid.uuid4().hex[:8]}"
                    if 'createdAt' not in record:
                        record['createdAt'] = datetime.now(timezone.utc)
                    if 'updatedAt' not in record:
                        record['updatedAt'] = datetime.now(timezone.utc)
                    
                    # Save to database
                    result, warnings = await DatabaseFactory.save_document("user", record, [])
                    if result:
                        saved_valid += 1
                        if warnings and self.verbose:
                            print(f"  ⚠️ Valid record warnings: {warnings}")
                            
                except Exception as e:
                    if self.verbose:
                        print(f"  ⚠️ Failed to save valid record {i+1}: {e}")
            
            # Save invalid records
            for i, record in enumerate(invalid_records):
                try:
                    # Ensure required fields
                    if 'id' not in record:
                        record['id'] = f"generated_invalid_{i+1}_{uuid.uuid4().hex[:8]}"
                    if 'createdAt' not in record:
                        record['createdAt'] = datetime.now(timezone.utc)
                    if 'updatedAt' not in record:
                        record['updatedAt'] = datetime.now(timezone.utc)
                    
                    # Save to database (these may have validation warnings)
                    result, warnings = await DatabaseFactory.save_document("user", record, [])
                    if result:
                        saved_invalid += 1
                        if warnings and self.verbose:
                            print(f"  ⚠️ Invalid record warnings: {warnings}")
                            
                except Exception as e:
                    if self.verbose:
                        print(f"  ⚠️ Failed to save invalid record {i+1}: {e}")
            
            # Close database connection
            await DatabaseFactory.close()
            
            if self.verbose:
                print(f"  ✅ Saved {saved_valid}/{len(valid_records)} valid records")
                print(f"  ✅ Saved {saved_invalid}/{len(invalid_records)} invalid records")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to save generated records: {e}")
            # Ensure database connection is closed on error
            try:
                await DatabaseFactory.close()
            except:
                pass
            return False
    
    async def wipe_all_data(self, config_file: str) -> bool:
        """Wipe all data and exit (destructive operation)"""
        print(f"\n📋 Wiping data")
    
        try:
            result = subprocess.run(
                [sys.executable, "tests/test_data_setup.py", "--config", config_file, "--wipe"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=Path(__file__).parent.parent
            )
            
            if result.returncode == 0:
                print("✅ All data wiped successfully")
                return True
            else:
                print(f"❌ Data wipe failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Data wipe error: {e}")
            return False
    
    # async def run_test_suite(self, config: TestConfig) -> TestResult:
    #     """Run test suites for a single database config"""
    #     start_time = time.time()
        
    #     try:
    #         # Get test suites based on self.test_cases parameter
    #         # test_suites = get_test_cases(self.test_cases)
            
    #         total_passed = 0
    #         total_failed = 0
    #         total_tests = 0
            
    #         # Handle curl responses if provided
    #         curl_responses = {}
    #         if hasattr(self, 'curl_responses') and self.curl_responses:
    #             # Use pre-loaded responses (for validation mode)
    #             curl_responses = self.curl_responses
    #             if self.verbose:
    #                 print(f"📁 Using {len(curl_responses)} pre-loaded responses")
    #         elif isinstance(self.curl_mode, str):
    #             # Load responses from file (main() handles "execute" mode)
    #             curl_responses = self.load_curl_output_file(self.curl_mode) or {}
    #             if self.verbose:
    #                 print(f"📁 Using {len(curl_responses)} responses from {self.curl_mode}")
            
    #         print(f"  📊 Progress: Starting {len(self.test_cases)} test suites...")
            
    #         # Single loop - mode is determined by curl_file_handle and curl_responses parameters
    #         for test_name, test in self.test_cases.items():
    #             test_details, test_class = test  # Get the test class from the tuple
    #             print(f"  🧪 Running {test_details}...")
    #             if self.verbose:
    #                 print(f"  📊 Progress: {total_tests + 1} of {len(self.test_cases)}")
                
    #             # Extract FK validation state from config for validation mode
    #             fk_validation = None
    #             if curl_responses and hasattr(config, 'config_data') and config.config_data:
    #                 fk_validation = config.config_data.get('fk_validation', False)
                
    #             curl_file_handle = self.curl_manager.get_curl_file_handle() if self.curl_manager else None
    #             tester = test_class("", f"http://localhost:{self.server_port}", 
    #                               self.verbose, curl_file_handle=curl_file_handle, mode_name=config.name.replace(" ", "_"),
    #                               request_delay=self.request_delay, curl_responses=curl_responses, fk_validation=fk_validation)
                
    #             try:
    #                 success = tester.run_all_tests()
    #                 if success:
    #                     total_passed += 1
    #                     result_icon = "✅"
    #                 else:
    #                     total_failed += 1
    #                     result_icon = "❌"
    #                 total_tests += 1
                    
    #                 # Show progress after each test suite
    #                 print(f"  📊 Progress: {result_icon} {test_name} completed ({total_passed + total_failed}/{len(test_suites)})")
                    
    #             except Exception as e:
    #                 total_failed += 1
    #                 total_tests += 1
    #                 print(f"  📊 Progress: ❌ {test_name} failed with exception: {e}")
    #                 if self.verbose:
    #                     import traceback
    #                     traceback.print_exc()
            
    #         overall_success = total_failed == 0 and total_tests > 0
            
    #         return TestResult(
    #             config_name=config.name,
    #             success=overall_success,
    #             passed=total_passed,
    #             failed=total_failed,
    #             total=total_tests,
    #             duration=time.time() - start_time
    #         )
            
    #     except Exception as e:
    #         return TestResult(
    #             config_name=config.name,
    #             success=False,
    #             passed=0,
    #             failed=0,
    #             total=0,
    #             duration=time.time() - start_time,
    #             error=str(e)
    #         )
    #     finally:
    #         self.stop_server()
    
    # async def validate_response(self, source, config_file):
    #     """Unified validation function - handles both file and HTTP sources"""
    #     # Load config
    #     with open(config_file, 'r') as f:
    #         config_data = json.load(f)
        
    #     # Create TestConfig
    #     config = TestConfig(
    #         name=f"{config_data.get('database', 'unknown')} {'with' if config_data.get('fk_validation') else 'without'} FK validation",
    #         database=config_data.get('database', 'mongodb'),
    #         config_data=config_data
    #     )
        
    #     # Load or use responses
    #     if isinstance(source, str):
    #         # Source is filename - load responses
    #         curl_manager = CurlManager(self.verbose)
    #         responses = curl_manager.load_json_responses_file(source)
    #     else:
    #         # execute requests and process responses
    #         responses = runner.run_test_suite(tests, config_data, self.verbose)
    #         content = source.read()
    #         parser = CurlOutputParser(self.verbose)
    #         passes = parser.parse_curl_output(content)
    #         responses = passes[0][1] if passes else {}
        
    #     # Run validation
    #     runner = ComprehensiveTestRunner(
    #         verbose=self.verbose, curl=False, dbs=self.dbs,
    #         newdata=False, test_cases=self.test_cases, entity=self.entity,
    #         request_delay=self.request_delay
    #     )
        
    #     result = await runner.run_test_suite(responses, config_data, self.verbose)
        
    #     if result.success:
    #         print(f"✅ Validation: {config.name} - {result.passed}/{result.total} test suites passed")
    #     else:
    #         print(f"❌ Validation: {config.name} - FAILED")
        
    #     return result.success

    async def generate_curl(self):
        """Generate curl.sh only - no server, no data, no validation"""  
        print(f"📝 Generating curl.sh with unique URLs...")
        curl = CurlManager(self.verbose)
        curl.create_curl_script()
        
        for test_name, (test_description, test_class) in self.test_cases.items():
            if self.verbose:
                print(f"  📝 Generating {test_description}...")
            
            # Create test instance and get test cases array
            test_instance = test_class("", "", self.verbose)
            test_cases = test_instance.get_test_cases()
            
            # Write each test case directly to curl file
            curl_file = curl.get_curl_file_handle()
            if curl_file:
                curl_file.write(f"# ========== {test_description} ==========\n")
                for test_case in test_cases:
                    full_url = f"http://localhost:{self.server_port}{test_case.url}"
                    curl_file.write(f'execute_url "{test_case.method}" "{full_url}" "{test_case.description}"\n')
        
        # Close curl file
        curl.close_curl_file()
        
        print("✅ curl.sh generation complete")

    async def run_connection_test(self) -> bool:
        """Run no-op connectivity test"""
        print("  🔗 Running connectivity test...")
        start_time = time.time()
        for config in self.configurations:
            print(f"  📋 Testing configuration: {config.name}")
            self.start_server(self.create_config_file(config))
            try:
                import requests
                
                # Test basic endpoint
                response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=5)
                if response.status_code != 200:
                    return False
                
            except Exception as e:
                return False
        end_time = time.time()
        print(f"  ✅ Connectivity test completed in {end_time - start_time:.1f}s")
        return True


    async def run(self, results_file: str, config_file: str) -> bool:
        """Run tests using either file results or live HTTP requests"""
        if len(results_file) > 0:
            curl = CurlManager(self.verbose)
            results = curl.load_json_responses_file(results_file)
        else:
            results = None

        overall_success = True
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for test_type, (test_description, test_class) in self.test_cases.items():
            print(f"\n🧪 Running {test_description} tests...")
            test_obj = test_class("", f"http://localhost:{self.server_port}", self.verbose)
            
            suite_passed = 0
            suite_failed = 0
            suite_total = 0
            
            for test in test_obj.get_test_cases():
                suite_total += 1
                total_tests += 1
                if self.verbose:
                    print(f"  📝 Executing {test.description}...")
                
                try:
                    if results is None:
                        # Live HTTP request - returns (bool, dict)
                        http_status, result = self._execute_test(test_obj, test)
                    else:
                        # Use file results - status is int, need to compare
                        url_key = test.url
                        if url_key in results:
                            result = results[url_key]['response']
                            http_status = results[url_key]['status']
                        else:
                            print(f"  ❌ {test.description} - URL not found in results")
                            status, result = False, None
                    
                    status = http_status == test.expected_status

                    if status and result:
                        if self._verify_result(test, result):
                            print(f"  ✅ {test.description} passed")
                            suite_passed += 1
                            total_passed += 1
                        else:
                            print(f"  ❌ {test.description} failed - validation mismatch")
                            suite_failed += 1
                            total_failed += 1
                            overall_success = False
                    else:
                        print(f"  ❌ {test.description} failed")
                        suite_failed += 1
                        total_failed += 1
                        overall_success = False
                        
                except Exception as e:
                    print(f"  ❌ {test.description} failed: {e}")
                    suite_failed += 1
                    total_failed += 1
                    overall_success = False
            
            # Print suite summary
            print(f"  📊 {test_description}: {suite_passed} passed, {suite_failed} failed, {suite_total} total")
        
        # Print overall summary
        print(f"\n📊 FINAL SUMMARY: {total_passed} passed, {total_failed} failed, {total_tests} total")
        
        return overall_success
    
    def _execute_test(self, test_obj, test_case):
        """Execute single test case via HTTP"""
        return test_obj.make_api_request(test_case.method, test_case.url, expected_status=test_case.expected_status)
    
    def _verify_result(self, test_case, result):
        """Verify result matches TestCase expectations"""
        # Surface-level validation
        if test_case.expected_data_len is not None:
            if 'data' not in result:
                return False
            # For expected_data_len, data should be an array
            data = result['data']
            if not isinstance(data, list):
                # Convert singleton to array for consistent counting
                data = [data]
            if len(data) != test_case.expected_data_len:
                return False
        if test_case.expected_notification_len is not None:
            notifications = result.get('notifications', [])
            if len(notifications) != test_case.expected_notification_len:
                return False
        if test_case.expected_paging and 'pagination' not in result:
            return False
            
        # Deep validation for fixed records
        if test_case.expected_response is not None:
            return self._deep_validate(data, test_case.expected_response['data'])
            
        return True
    
    def _deep_validate(self, actual, expected):
        """Deep validation - recursively compare actual vs expected response"""
        if type(actual) != type(expected):
            return False
            
        if isinstance(expected, dict):
            for key, expected_value in expected.items():
                if key not in actual:
                    return False
                if not self._deep_validate(actual[key], expected_value):
                    return False
        elif isinstance(expected, list):
            if len(actual) != len(expected):
                return False
            for i, expected_item in enumerate(expected):
                if not self._deep_validate(actual[i], expected_item):
                    return False
        else:
            # Primitive values - direct comparison
            if actual != expected:
                return False
                
        return True



    def print_summary(self, results: List[TestResult]) -> bool:
        """Print comprehensive summary"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST SUMMARY")
        print('='*80)
        
        successful_configs = sum(1 for r in results if r.success)
        total_duration = sum(r.duration for r in results)
        
        print(f"Configurations: {successful_configs}/{len(results)} passed")
        print(f"Total duration: {total_duration:.1f}s")
        print()
        
        for result in results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"{status} {result.config_name}")
            if result.total > 0:
                print(f"     {result.passed}/{result.total} test suites passed")
            if result.error:
                print(f"     Error: {result.error}")
        
        print(f"\n{'='*80}")
        if successful_configs == len(results):
            print("🎉 ALL CONFIGURATIONS PASSED!")
        else:
            print("💥 SOME CONFIGURATIONS FAILED!")
        
        return successful_configs == len(results)
    
        try:
            if os.path.exists("tests/temp_test_config.json"):
                os.remove("tests/temp_test_config.json")
        except:
            pass
        self.stop_server()

# Lightweight orchestrator for new test framework
class ComprehensiveTestOrchestrator:
    """Simple orchestrator that doesn't manage server lifecycle"""
    
    def __init__(self, server_url: str, verbose: bool):
        self.server_url = server_url
        self.verbose = verbose


def get_dbs(args):
    dbs = []
    if args.mongo:
        dbs.append("mongodb")
    if args.es:
        dbs.append("elasticsearch")
    return dbs if dbs else ["mongodb", "elasticsearch"]  # Default to both if none specified

def get_test_cases(requested_tests: List[str]) -> Dict[str, Tuple[str, type]]:
    """Convert test case names to {display_name: test_class} dict"""
    available_tests: Dict[str, Tuple[str, type]] = {
        'basic': ("Basic API Tests", BasicAPITester),
        'view': ("View Parameter Tests", ViewParameterTester),
        'page': ("Pagination Tests", PaginationTester),
        'sort': ("Sorting Tests", SortingTester),
        'filter': ("Filtering Tests", FilteringTester),
        'combo': ("Combination Tests", CombinationTester),
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

def get_configs(args, dbs):
    # Define test configurations
    all_configs = [
        TestConfig(
            name="MongoDB without FK validation",
            database="mongodb",
            config_data={
                "database": "mongodb",
                "db_uri": "mongodb://localhost:27017",
                "db_name": "eventMgr",
                "fk_validation": "",
                "unique_validation": False
            }
        ),
        TestConfig(
            name="MongoDB with FK validation",
            database="mongodb", 
            config_data={
                "database": "mongodb",
                "db_uri": "mongodb://localhost:27017", 
                "db_name": "eventMgr",
                "fk_validation": "multiple",
                "unique_validation": True
            }
        ),
        TestConfig(
            name="Elasticsearch without FK validation",
            database="elasticsearch",
            config_data={
                "database": "elasticsearch",
                "db_uri": "http://localhost:9200",
                "db_name": "eventMgr", 
                "fk_validation": "",
                "unique_validation": False
            }
        ),
        TestConfig(
            name="Elasticsearch with FK validation",
            database="elasticsearch",
            config_data={
                "database": "elasticsearch",
                    "db_uri": "http://localhost:9200",
                    "db_name": "eventMgr",
                    "fk_validation": "multiple",
                    "unique_validation": True
                }
            )
        ]
        
    # Filter configurations based on database flags
    if len(dbs) == 0:
        # No specific database selected - use all configs
        return all_configs
    else:
        # Filter based on selected databases
        return [config for config in all_configs if config.database in dbs]
    


async def main():
    """Main function with clean curl orchestration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive test runner')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', nargs='?', const=True, default=False,
                       help='Curl mode: no arg=generate only, "execute"=run curl.sh and validate, filename=validate from file')
    parser.add_argument('--mongo', action='store_true',
                       help='Test MongoDB configurations only')
    parser.add_argument('--es', action='store_true', 
                       help='Test Elasticsearch configurations only')
    parser.add_argument('--connection', action='store_true',
                       help='Run connectivity tests only')
    parser.add_argument('--newdata', action='store_true',
                       help='Wipe all data and create fresh test data with known validation issues')
    parser.add_argument('--newdata-only', action='store_true',
                       help='Only Wipe all data and create fresh test data with known validation issues')
    parser.add_argument('--tests', nargs='+', 
                       choices=['basic', 'view', 'page', 'filter', 'sort'],
                       help='Test cases to run (choices: basic, view, page, filter, sort). Can specify multiple: --tests basic sort')
    parser.add_argument('--wipe', action='store_true',
                       help='DESTRUCTIVE: Wipe all data and exit (must be the only argument)')
    parser.add_argument('--entity', default="user",
                       help='Entity to test (default: user)')
    parser.add_argument('--delay', type=float, default=0.0,
                       help='Delay between requests in seconds (default: 0.0 - no delay)')
    parser.add_argument('--config', 
                       help='Config file to use for validation (required when using --curl <file>)')
    args = parser.parse_args()
    
    # Validate arguments - require --config when using --curl <file>
    if isinstance(args.curl, str) and args.curl != "execute":
        if not hasattr(args, 'config') or not args.config:
            parser.error("--config <file> is required when using --curl <file> to know the FK validation state")
    
    dbs = get_dbs(args)
    configs = get_configs(args, dbs)
    test_cases: Dict[str, Tuple[str, type]] = get_test_cases(args.tests)

    runner = ComprehensiveTestRunner(verbose=args.verbose, dbs=dbs, configurations=configs)
    # Handle special modes first
    if args.wipe:
        print("  Only running wipe mode - no tests will be executed")
        for config in configs:
            await runner.wipe_all_data(runner.create_config_file(config))
        return 0

    if args.connection:
        print("  Running connectivity test")
        runner = ComprehensiveTestRunner(verbose=args.verbose, dbs=dbs, connection=True)
        await runner.run_connection_test()
        return 0

    if args.newdata_only:
        if not args.config:
            print(f"❌ --config <file> is required when using --newdata-only to know the FK validation state")
            return
        success = await runner.wipe_all_data(args.config)
        if not success:
            print(f"❌ Failed to wipe data for {args.config})")
            return 1
        success = await runner.create_test_data(args.config) 
        if not success:
            print(f"❌ Failed to create test data for {args.config}")
            return 1
        print("✅ Fresh test data created successfully")


    # Handle curl modes with clean orchestration
    runner = ComprehensiveTestRunner(verbose=args.verbose, dbs=dbs, connection=True, test_cases=test_cases, entity=args.entity, request_delay=args.delay)
    try:
        if args.curl is True:
            # Curl Mode 1: Generate curl.sh
            await runner.generate_curl()    # no config file needed
            print("Run script tests/curl.sh > results.json to execute the generated commands")
            print("Recommend --newdata-only --config <config_file> to wipe and create new before each run")
            print("Then run --curl results.json --config <config_file> to validate the responses")
            return 0
            
        elif args.curl == "execute" or args.curl is None:
            # Mode 2: Orchestrated 3-step process or real time execution
            if args.curl:
                await runner.generate_curl()

            success = 0
            
            # Execute curl.sh for each configuration
            for i, config in enumerate(configs):
                print(f"🚀 Pass {i+1} or {len(configs)}: {config.name}")
                
                config_file = runner.create_config_file(config)
                
                try:
                    if not runner.start_server(config_file):
                        print(f"❌ Failed to start server for {config.name}")
                        return 1
                
                    # Create test data if requested
                    if args.newdata:
                        success = await runner.wipe_all_data(config_file)
                        if not success:
                            print(f"❌ Failed to wipe data for {config.name}")
                            return 1
                        success = await runner.create_test_data(config_file)
                        if not success:
                            print(f"❌ Failed to create test data for {config.name}")
                            return 1

                    if args.curl:
                        # create ouput file with server config and the output of curl.sh
                        # First call: create/truncate the file and write config_file content
                        file_name = f'tests/curl_output_pass_{i+1}.txt'
                        with open(file_name, "w") as f:
                            result = subprocess.run(['bash', 'tests/curl.sh'], stdout=f, stderr=subprocess.PIPE, text=True, timeout=300)

                            if result.returncode != 0:
                                print(f"❌ curl.sh execution failed for {config.name} with return code {result.returncode}")
                                if result.stderr:
                                    print(f"   Error: {result.stderr}")
                                return 1

                    status = await runner.run(file_name if args.curl else '', config_file)
                    success += status != 0

                finally:
                    runner.stop_server()
            
            return success

        elif isinstance(args.curl, str):
            # Mode 3: Validate from file with specified config
            print(f"📁 Validating responses from file: {args.curl} Using config file: {args.config}")
            
            success = await runner.run(args.curl, args.config)
            return 0 if success else 1
            
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test runner failed: {e}")
        return 1
    finally:
        # Cleanup temp files
        try:
            import os
            if os.path.exists("tests/temp_curl_output.txt"):
                os.remove("tests/temp_curl_output.txt")
            if os.path.exists("tests/temp_test_config.json"):
                os.remove("tests/temp_test_config.json")
        except:
            pass

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))