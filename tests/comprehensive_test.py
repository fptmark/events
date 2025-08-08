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

from tests.base_test import TestCounter
from tests.test_basic import BasicAPITester
from tests.test_view import ViewParameterTester
from tests.test_pagination import PaginationTester
from tests.test_sorting import SortingTester
from tests.test_filtering import FilteringTester
from tests.test_combinations import CombinationTester
from tests.datagen import DataGen
from tests.curl import CurlManager
from tests.base_test import TestCase
from tests.data_verifier import DataVerifier
# import tests.utils as utils
from app.config import Config


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
        self.server_process: subprocess.Popen[str]
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
    
    async def start_server(self, config_file: str, newdata: bool) -> bool:
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
            
            success = False
            # Wait for server to be ready
            for attempt in range(30):
                try:
                    import requests
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        success = True
                        if self.verbose:
                            print(f"  ✅ Server ready (attempt {attempt + 1})")
                        break
                except:
                    pass
                time.sleep(1)
            
            if not success:
                print("  ❌ Server failed to start")
                return False
            
        except Exception as e:
            print(f"  ❌ Server start error: {e}")
            return False

        # Create test data if requested
        if newdata:
            await self.create_new_data(config_file)
        return True
    
    async def create_new_data(self, config_file: str) -> bool:
        if not config_file:
            print(f"❌ --config <file> is required when using --newdata-only to know the FK validation state")
            return False
        success = await self.wipe_all_data(config_file)
        if not success:
            print(f"❌ Failed to wipe data for {config_file}")
            return False
        success = await self.create_test_data(config_file)
        if not success:
            print(f"❌ Failed to create test data for {config_file}")
            return False
        return True

    
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
            print("  🧹 Creating fresh test data...")
        
        try:
            data_gen = DataGen(self.entity)
            valid, invalid = data_gen.generate_records(50, 20, self.verbose)
            
            # Save all generated records (includes both random + known test users)
            success = await data_gen.save_generated_records_to_database(config_file, valid, invalid, self.verbose)
            
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
            await self.start_server(self.create_config_file(config), False)
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

        total_counter = TestCounter()

        config = Config.initialize(config_file)
        
        for test_type, (test_description, test_class) in self.test_cases.items():
            print(f"\n🧪 Running {test_description} tests...")
            test_obj = test_class("", f"http://localhost:{self.server_port}", self.verbose)
            
            suite_counter = TestCounter()
            
            for test in test_obj.get_test_cases():
                if self.verbose:
                    print(f"  📝 Processing {test.description}...    {test.url}")
                
                try:
                    if results is None:
                        # Live HTTP request - returns (bool, dict)
                        http_status, result = test_obj.make_api_request(test_obj.method, test_obj.url, expected_status=test_obj.expected_status)
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
                        verifier = DataVerifier(test, result, config, self.verbose)
                        if verifier.verify_test_case(): # test_class.generate_expected_response() ):
                            print(f"  ✅ {test.description} passed")
                            suite_counter.pass_test()
                        else:
                            print(f"  ❌ {test.description} failed - validation mismatch")
                            suite_counter.fail_test()
                    else:
                        print(f"  ❌ {test.description} failed")
                        suite_counter.fail_test()
                        
                except Exception as e:
                    print(f"  ❌ {test.description} failed: {e}")
                    suite_counter.fail_test()
            
            total_counter.update(suite_counter)
            # Print suite summary
            print(f"  {suite_counter.summary(test_description)}")
        
        # Print overall summary
        print(f"\n{total_counter.summary('FINAL SUMMARY')}")
        
        return total_counter.failed == 0
    


    def cleanup(self):
        """Clean up temporary files"""
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
        success = await runner.create_new_data(args.config)

    # Handle curl modes with clean orchestration
    runner = ComprehensiveTestRunner(verbose=args.verbose, dbs=dbs, connection=True, test_cases=test_cases, entity=args.entity, request_delay=args.delay)
    try:
        if args.curl is True:
            # Curl Mode 1: Generate curl.sh
            await runner.generate_curl()    # no config file needed
            print("Run script tests/curl.sh > results.json to execute the generated commands")
            print("Then run --curl <results.json> --config <config_file> to validate the responses.  This will start the server to get the metadata and reset the database")
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
                    if not runner.start_server(config_file, args.newdata):
                    #     print(f"❌ Failed to start server for {config.name}")
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
            status = await runner.create_new_data(args.config)
            if not status:
                return 1
            
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