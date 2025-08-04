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

from tests.common_test_framework import CommonTestFramework
from tests.test_basic import BasicAPITester
from tests.test_view import ViewParameterTester
from tests.test_pagination import PaginationTester
from tests.test_sorting import SortingTester
from tests.test_filtering import FilteringTester
from tests.test_combinations import CombinationTester
from tests.create_data import CreateData

class CurlResponse:
    """Mock response object that mimics requests.Response for curl results"""
    def __init__(self, status_code: int, text: str, url: str, elapsed_time: float):
        self.status_code = status_code
        self.text = text
        self.url = url
        self.elapsed = elapsed_time
        self._json_data = None
    
    def json(self):
        """Parse JSON response like requests.Response.json()"""
        if self._json_data is None:
            try:
                import json
                self._json_data = json.loads(self.text)
            except json.JSONDecodeError:
                self._json_data = {}
        return self._json_data

class CurlOutputParser:
    """Parse curl.sh output and convert to response objects"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.responses = {}  # url -> CurlResponse
        self.config = None  # Extracted config from curl output
    
    def parse_curl_output(self, output: str) -> List[Tuple[dict, Dict[str, CurlResponse]]]:
        """Parse curl output and return list of (config, responses) tuples for each pass"""
        passes = []
        lines = output.strip().split('\n')
        
        current_config = None
        current_responses = {}
        current_json = ""
        current_result = None
        in_config = False
        config_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line == 'CONFIG_START':
                in_config = True
                config_lines = []
            elif line == 'CONFIG_END':
                in_config = False
                # Parse config JSON
                try:
                    config_text = '\n'.join(config_lines)
                    current_config = json.loads(config_text)
                    if self.verbose:
                        print(f"📋 Found config: {current_config.get('database', 'unknown')} FK:{current_config.get('fk_validation', 'off')}")
                except json.JSONDecodeError as e:
                    if self.verbose:
                        print(f"⚠️ Warning: Could not parse config: {e}")
                    current_config = {}
            elif in_config:
                config_lines.append(line)
            elif line.startswith('CURL_RESULT|'):
                # Parse result metadata
                current_result = self._parse_result_line(line)
            elif line == 'CURL_END':
                # End of current response, create CurlResponse object
                if current_result and current_json:
                    response = CurlResponse(
                        status_code=current_result['status'],
                        text=current_json.strip(),
                        url=current_result['url'],
                        elapsed_time=current_result['time']
                    )
                    current_responses[current_result['url']] = response
                    if self.verbose:
                        print(f"📥 Parsed curl response: {current_result['status']} for {current_result['url']}")
                
                # Reset for next response
                current_json = ""
                current_result = None
            elif current_result and not line.startswith('=== ') and line.strip():
                # Accumulate JSON response body
                current_json += line + '\n'
            
            # Check if we're at the start of a new config section (next CONFIG_START or EOF)
            if i + 1 < len(lines) and lines[i + 1] == 'CONFIG_START' and current_config is not None:
                # End of current pass - save it
                passes.append((current_config, current_responses))
                current_config = None
                current_responses = {}
            
            i += 1
        
        # Save the last pass if we have one
        if current_config is not None:
            passes.append((current_config, current_responses))
        
        if self.verbose:
            print(f"📊 Parsed {len(passes)} configuration passes")
            
        return passes
    
    def _parse_result_line(self, line: str) -> Dict[str, Any]:
        """Parse CURL_RESULT line into components"""
        # Format: CURL_RESULT|STATUS:200|TIME:0.004|URL:http://...
        try:
            parts = line.split('|')[1:]  # Skip CURL_RESULT prefix
            result = {}
            
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    if key == 'STATUS':
                        result['status'] = int(value)
                    elif key == 'TIME':
                        result['time'] = float(value)
                    elif key == 'URL':
                        result['url'] = value
            
            return result
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Warning: Could not parse result line: {line} - {e}")
            return {}

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
    
    def __init__(self, verbose: bool = False, curl=False, dbs: List[str] = [],
                 connection: bool = False, newdata: bool = False, wipe: bool = False, test_cases: List[str] = None, entity: str = "user",
                 request_delay: float = 0.0, json_output: bool = False):
        self.server_port = 5500
        self.server_process = None
        self.verbose = verbose
        self.curl_mode = curl  # Store the curl mode (False, True, "execute", or filename)
        self.curl = None
        
        # Initialize curl file handling based on mode
        if curl is True:
            # Mode: Generate curl.sh only
            try:
                self.curl = open('tests/curl.sh', 'w')
                self.curl.write('#!/bin/bash\n')
                self.curl.write('# Generated curl commands from comprehensive test execution\n') 
                self.curl.write('# Auto-generated by --curl mode\n\n')
                print("📁 Initialized tests/curl.sh - will generate curl commands only")
            except Exception as e:
                print(f"⚠️ Warning: Could not initialize tests/curl.sh: {e}")
                self.curl = None
        elif curl == "execute":
            print("📁 Will execute tests/curl.sh and validate responses")
        elif isinstance(curl, str):
            print(f"📁 Will validate responses from file: {curl}")
        # Mode: curl is False - normal requests mode (no action needed)
        self.dbs = dbs
        self.connection = connection
        self.newdata = newdata
        self.wipe = wipe
        self.test_cases = test_cases or ['basic', 'view', 'page', 'filter', 'sort']  # Default to all tests
        self.entity = entity
        self.request_delay = request_delay
        self.json_output = json_output
        
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
        if len(self.dbs) == 0:
            # No specific database selected - use all configs
            self.test_configs = all_configs
        else:
            # Filter based on selected databases
            self.test_configs = [config for config in all_configs 
                                if config.database in self.dbs]
    
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
            
            create = CreateData(metadata, self.entity)
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
    
    async def run_test_suite(self, config: TestConfig) -> TestResult:
        """Run the new clean test suite - assumes server and data are already set up"""
        start_time = time.time()
        
        try:
            # config_file = self.create_config_file(config)
            
            # # Run tests using new framework
            # orchestrator = ComprehensiveTestOrchestrator(
            #     f"http://localhost:{self.server_port}", 
            #     self.verbose, 
            #     self.curl
            # )
            
            # Run selected test suites based on test_cases parameter
            
            # Map test case names to test classes
            available_tests = {
                'basic': ("Basic API Tests", BasicAPITester),
                'view': ("View Parameter Tests", ViewParameterTester),
                'page': ("Pagination Tests", PaginationTester),
                'sort': ("Sorting Tests", SortingTester),
                'filter': ("Filtering Tests", FilteringTester),
            }

            test_suites = []
            if self.test_cases is None:
                # If no specific test cases provided, run all available tests
                test_suites = list(available_tests.values())

            # Add selected test suites
            for test_case in self.test_cases:
                if test_case in available_tests:
                    test_suites.append(available_tests[test_case])
                else:
                    print(f"⚠️ Warning: Unknown test case '{test_case}' ignored")
            
            total_passed = 0
            total_failed = 0
            total_tests = 0
            
            # Handle curl responses if provided
            curl_responses = {}
            if isinstance(self.curl_mode, str):
                # Load responses from file (main() handles "execute" mode)
                curl_responses = self.load_curl_output_file(self.curl_mode) or {}
                if self.verbose:
                    print(f"📁 Using {len(curl_responses)} responses from {self.curl_mode}")
            
            print(f"  📊 Progress: Starting {len(test_suites)} test suites...")
            
            # Single loop - mode is determined by curl_file_handle and curl_responses parameters
            for test_name, test_class in test_suites:
                if self.verbose:
                    print(f"  🧪 Running {test_name}...")
                else:
                    print(f"  📊 Progress: {total_tests + 1}/{len(test_suites)} - {test_name}")
                
                tester = test_class("", f"http://localhost:{self.server_port}", 
                                  self.verbose, curl_file_handle=self.curl, mode_name=config.name.replace(" ", "_"),
                                  request_delay=self.request_delay, curl_responses=curl_responses)
                
                try:
                    success = tester.run_all_tests()
                    if success:
                        total_passed += 1
                        result_icon = "✅"
                    else:
                        total_failed += 1
                        result_icon = "❌"
                    total_tests += 1
                    
                    # Show progress after each test suite
                    print(f"  📊 Progress: {result_icon} {test_name} completed ({total_passed + total_failed}/{len(test_suites)})")
                    
                except Exception as e:
                    total_failed += 1
                    total_tests += 1
                    print(f"  📊 Progress: ❌ {test_name} failed with exception: {e}")
                    if self.verbose:
                        import traceback
                        traceback.print_exc()
            
            overall_success = total_failed == 0 and total_tests > 0
            
            return TestResult(
                config_name=config.name,
                success=overall_success,
                passed=total_passed,
                failed=total_failed,
                total=total_tests,
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                config_name=config.name,
                success=False,
                passed=0,
                failed=0,
                total=0,
                duration=time.time() - start_time,
                error=str(e)
            )
        finally:
            self.stop_server()
    
    async def generate_only(self):
        """Generate curl.sh only - no server, no data, no validation"""
        print(f"📝 Generating curl.sh with unique URLs...")
        
        # Use only the first config to generate unique URLs once
        config = self.test_configs[0]
        print(f"📋 Generating commands using: {config.name}")
        
        # Map test case names to test classes
        available_tests = {
            'basic': ("Basic API Tests", BasicAPITester),
            'view': ("View Parameter Tests", ViewParameterTester),
            'page': ("Pagination Tests", PaginationTester),
            'sort': ("Sorting Tests", SortingTester),
            'filter': ("Filtering Tests", FilteringTester),
        }
        
        test_suites = []
        if self.test_cases is None:
            test_suites = list(available_tests.values())
        else:
            for test_case in self.test_cases:
                if test_case in available_tests:
                    test_suites.append(available_tests[test_case])
        
        # Generate curl commands once (no server needed)
        for test_name, test_class in test_suites:
            if self.verbose:
                print(f"  📝 Generating {test_name}...")
            
            # Config file not needed for curl generation - test class won't connect to database
            tester = test_class("", f"http://localhost:{self.server_port}", 
                              self.verbose, curl_file_handle=self.curl, 
                              mode_name="curl_generation",
                              request_delay=self.request_delay, curl_responses=None,
                              json_output=getattr(self, 'json_output', False))
            
            # This will generate curl commands only
            tester.run_all_tests()
        
        # Close curl file
        if self.curl:
            self.curl.close()
            self.curl = None
        
        print("✅ curl.sh generation complete")

    async def run_connection_test(self) -> bool:
        """Run no-op connectivity test"""
        print("  🔗 Running connectivity test...")
        start_time = time.time()
        for config in self.test_configs:
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


    async def run_tests(self) -> List[TestResult]:
        """Run all test configurations"""
        print(f"\n🚀 Starting {len(self.test_configs)} test configurations...")
        results = []
        i = 0
        for config in self.test_configs:
            i += 1
            print(f"\n📋 Testing ({i}/{len(self.test_configs)}): {config.name}")
            print("-" * 60)

            config_file = self.create_config_file(config)
            status = self.start_server(config_file)
            if status:
                if self.newdata:
                    success = await self.wipe_all_data(config_file)
                    if not success:
                        print(f"❌ Failed to wipe data for {config.name}")
                        return []
                    success = await self.create_test_data(config_file)
                    if not success:
                        print(f"❌ Failed to create test data for {config.name}")
                        return []
            
                result = await self.run_test_suite(config)
                results.append(result)
                
                if result.success:
                    print(f"✅ Configuration {i}/{len(self.test_configs)} - {config.name}: {result.passed}/{result.total} test suites passed ({result.duration:.1f}s)")
                else:
                    print(f"❌ Configuration {i}/{len(self.test_configs)} - {config.name}: FAILED - {result.error} ({result.duration:.1f}s)")
                self.stop_server()
        return results

    
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
    
    def execute_curl_and_parse(self, config: TestConfig) -> Optional[Dict[str, CurlResponse]]:
        """Execute curl.sh and parse the output into response objects"""
        if self.curl_mode is not True:
            return None  # Only execute in generate+execute mode
        
        if not self.curl:
            print("⚠️ Warning: No curl.sh file generated")
            return None
        
        # Close the curl file to ensure all commands are written
        self.curl.close()
        self.curl = None
        
        # Make curl.sh executable
        try:
            import subprocess
            subprocess.run(['chmod', '+x', 'tests/curl.sh'], check=True, capture_output=True)
            
            print(f"🚀 Executing curl.sh for {config.name}...")
            
            # Execute curl.sh and capture output
            result = subprocess.run(['bash', 'tests/curl.sh'], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"❌ curl.sh execution failed with return code {result.returncode}")
                if result.stderr:
                    print(f"   Error: {result.stderr}")
                return None
            
            # Parse the curl output
            parser = CurlOutputParser(self.verbose)
            responses = parser.parse_curl_output(result.stdout)
            
            print(f"✅ Parsed {len(responses)} curl responses")
            return responses
            
        except subprocess.TimeoutExpired:
            print("❌ curl.sh execution timed out (5 minutes)")
            return None
        except Exception as e:
            print(f"❌ Error executing curl.sh: {e}")
            return None
    
    def load_curl_output_file(self, filename: str) -> Optional[List[Tuple[dict, Dict[str, CurlResponse]]]]:
        """Load and parse existing curl output file with multiple passes"""
        try:
            with open(filename, 'r') as f:
                content = f.read()
            
            parser = CurlOutputParser(self.verbose)
            passes = parser.parse_curl_output(content)
            
            total_responses = sum(len(responses) for _, responses in passes)
            print(f"✅ Loaded {len(passes)} passes with {total_responses} total responses from {filename}")
            return passes
            
        except FileNotFoundError:
            print(f"❌ Curl output file not found: {filename}")
            return None
        except Exception as e:
            print(f"❌ Error loading curl output file: {e}")
            return None
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            if os.path.exists("tests/temp_test_config.json"):
                os.remove("tests/temp_test_config.json")
        except:
            pass
        # Close curl file if open
        if self.curl:
            try:
                self.curl.close()
            except:
                pass
        self.stop_server()

# Lightweight orchestrator for new test framework
class ComprehensiveTestOrchestrator:
    """Simple orchestrator that doesn't manage server lifecycle"""
    
    def __init__(self, server_url: str, verbose: bool, curl_file):
        self.server_url = server_url
        self.verbose = verbose
        self.curl_file = curl_file

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
    parser.add_argument('--tests', nargs='+', 
                       choices=['basic', 'view', 'page', 'filter', 'sort'],
                       help='Test cases to run (choices: basic, view, page, filter, sort). Can specify multiple: --tests basic sort')
    parser.add_argument('--wipe', action='store_true',
                       help='DESTRUCTIVE: Wipe all data and exit (must be the only argument)')
    parser.add_argument('--entity', default="user",
                       help='Entity to test (default: user)')
    parser.add_argument('--delay', type=float, default=0.0,
                       help='Delay between requests in seconds (default: 0.0 - no delay)')
    parser.add_argument('--json', action='store_true',
                       help='Output everything in structured JSON format for easier parsing')
    args = parser.parse_args()
    
    dbs = []
    if args.mongo:
        dbs.append("mongodb")
    if args.es:
        dbs.append("elasticsearch")

    # Handle special modes first
    if args.wipe:
        print("  Only running wipe mode - no tests will be executed")
        runner = ComprehensiveTestRunner(verbose=args.verbose, curl=False, dbs=dbs, wipe=True)
        for config in runner.test_configs:
            await runner.wipe_all_data(runner.create_config_file(config))
        return 0

    if args.connection:
        print("  Running connectivity test")
        runner = ComprehensiveTestRunner(verbose=args.verbose, curl=False, dbs=dbs, connection=True)
        await runner.run_connection_test()
        return 0

    # Handle curl modes with clean orchestration
    try:
        if args.curl is True:
            # Mode 1: Generate curl.sh only (no server, no data)
            print("📝 Generating curl.sh...")
            runner = ComprehensiveTestRunner(
                verbose=args.verbose, curl=True, dbs=dbs, 
                test_cases=args.tests, entity=args.entity, request_delay=args.delay
            )
            runner.json_output = args.json
            await runner.generate_only()
            print("✅ Generated curl.sh - run with --curl execute to validate")
            return 0
            
        elif args.curl == "execute":
            # Mode 2: Orchestrated 3-step process
            print("🚀 Executing 3-step curl process...")
            
            # Step 1: Generate curl.sh
            print("📝 Step 1: Generating curl.sh...")
            runner_gen = ComprehensiveTestRunner(
                verbose=args.verbose, curl=True, dbs=dbs,
                test_cases=args.tests, entity=args.entity, request_delay=args.delay
            )
            await runner_gen.generate_only()
            
            # Step 2: Execute curl.sh for all configurations
            print("🚀 Step 2: Executing curl.sh for all configurations...")
            
            runner_exec = ComprehensiveTestRunner(
                verbose=args.verbose, curl=False, dbs=dbs,
                newdata=args.newdata, test_cases=args.tests, entity=args.entity,
                request_delay=args.delay
            )
            
            # Store original curl.sh content (without config header)
            with open('tests/curl.sh', 'r') as f:
                original_curl_content = f.read()
            
            all_output = []
            
            # Execute curl.sh for each configuration
            for i, config in enumerate(runner_exec.test_configs):
                print(f"🚀 Pass {i+1}/{len(runner_exec.test_configs)}: {config.name}")
                
                config_file = runner_exec.create_config_file(config)
                
                if not runner_exec.start_server(config_file):
                    print(f"❌ Failed to start server for {config.name}")
                    return 1
                
                try:
                    # Create test data if requested
                    if args.newdata:
                        success = await runner_exec.wipe_all_data(config_file)
                        if not success:
                            print(f"❌ Failed to wipe data for {config.name}")
                            return 1
                        success = await runner_exec.create_test_data(config_file)
                        if not success:
                            print(f"❌ Failed to create test data for {config.name}")
                            return 1
                    
                    # Add config info to curl.sh for this pass
                    config_header = f"""#!/bin/bash
# Config used for this execution pass
echo "CONFIG_START"
cat "{config_file}"
echo "CONFIG_END"

"""
                    
                    with open('tests/curl.sh', 'w') as f:
                        f.write(config_header + original_curl_content[original_curl_content.find('\n')+1:])
                    
                    # Execute curl.sh and capture output
                    import subprocess
                    result = subprocess.run(['bash', 'tests/curl.sh'], 
                                          capture_output=True, text=True, timeout=300)
                    
                    if result.returncode != 0:
                        print(f"❌ curl.sh execution failed for {config.name} with return code {result.returncode}")
                        if result.stderr:
                            print(f"   Error: {result.stderr}")
                        return 1
                    
                    # Collect output from this pass
                    all_output.append(result.stdout)
                    print(f"✅ Pass {i+1} completed: {len(result.stdout)} chars captured")
                    
                finally:
                    runner_exec.stop_server()
            
            # Output all passes concatenated to stdout for redirection
            print("📤 All curl execution output:")
            for output in all_output:
                print(output)
            
            return 0
            
        elif isinstance(args.curl, str):
            # Mode 3: Validate from file (with multiple passes)
            print(f"📁 Validating responses from file: {args.curl}")
            
            # Load all passes from file
            runner = ComprehensiveTestRunner(
                verbose=args.verbose, curl=False, dbs=dbs,
                newdata=False, test_cases=args.tests, entity=args.entity,
                request_delay=args.delay
            )
            
            passes = runner.load_curl_output_file(args.curl)
            if not passes:
                print("❌ Failed to load curl output file")
                return 1
            
            # Validate each pass with its corresponding config
            all_results = []
            for i, (config_data, responses) in enumerate(passes):
                print(f"\n📋 Validating pass {i+1}/{len(passes)}: {config_data.get('database', 'unknown')} FK:{config_data.get('fk_validation', 'off')}")
                print("-" * 60)
                
                # Create TestConfig from the loaded config data
                from dataclasses import dataclass
                config = TestConfig(
                    name=f"{config_data.get('database', 'unknown')} {'with' if config_data.get('fk_validation') else 'without'} FK validation",
                    database=config_data.get('database', 'mongodb'),
                    config_data=config_data
                )
                
                # Start server with this config for validation
                config_file = runner.create_config_file(config)
                if not runner.start_server(config_file):
                    print(f"❌ Failed to start server for {config.name}")
                    continue
                
                try:
                    # Create test data if needed
                    if args.newdata:
                        success = await runner.wipe_all_data(config_file)
                        if not success:
                            print(f"❌ Failed to wipe data for {config.name}")
                            continue
                        success = await runner.create_test_data(config_file)
                        if not success:
                            print(f"❌ Failed to create test data for {config.name}")
                            continue
                    
                    # Set responses for validation
                    runner.curl_responses = responses
                    runner.curl_mode = args.curl
                    
                    # Run validation tests
                    result = await runner.run_test_suite(config)
                    all_results.append(result)
                    
                    if result.success:
                        print(f"✅ Pass {i+1}: {config.name} - {result.passed}/{result.total} test suites passed")
                    else:
                        print(f"❌ Pass {i+1}: {config.name} - FAILED")
                        
                finally:
                    runner.stop_server()
            
            # Print overall summary
            success = runner.print_summary(all_results)
            return 0 if success else 1
            
        else:
            # Mode 4: Normal HTTP requests (with server and data)
            runner = ComprehensiveTestRunner(
                verbose=args.verbose, curl=False, dbs=dbs,
                newdata=args.newdata, test_cases=args.tests, entity=args.entity,
                request_delay=args.delay
            )
            results = await runner.run_tests()
            success = runner.print_summary(results)
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