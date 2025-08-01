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
from typing import Dict, List, Tuple, Optional
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
    
    def __init__(self, verbose: bool = False, curl: bool = False, dbs: List[str] = [],
                 connection: bool = False, newdata: bool = False, wipe: bool = False, basic: bool = False):
        self.server_port = 5500
        self.server_process = None
        self.verbose = verbose
        self.curl = None
        
        # Initialize curl file once at the start of comprehensive testing
        if curl:
            try:
                self.curl = open('tests/curl.sh', 'w')
                self.curl.write('#!/bin/bash\n')
                self.curl.write('# Generated curl commands from comprehensive test execution\n')
                self.curl.write('# Run: chmod +x tests/curl.sh && ./tests/curl.sh\n\n')
                print("📁 Initialized tests/curl.sh - comprehensive test API calls will be logged")
            except Exception as e:
                print(f"⚠️ Warning: Could not initialize tests/curl.sh: {e}")
                self.curl = None
        self.dbs = dbs
        self.connection = connection
        self.newdata = newdata
        self.wipe = wipe
        self.basic = basic
        
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
            result = subprocess.run(
                [sys.executable, "tests/test_data_setup.py", "--config", config_file, "--newdata"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=Path(__file__).parent.parent
            )
            
            if result.returncode == 0:
                if self.verbose:
                    print("  ✅ Test data created successfully")
                return True
            else:
                print(f"  ❌ Test data creation failed: {result.stderr}")
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
    
    async def run_test_suite(self, config: TestConfig) -> TestResult:
        """Run the new clean test suite"""
        start_time = time.time()
        
        try:
            config_file = self.create_config_file(config)
            
            if not self.start_server(config_file):
                return TestResult(
                    config_name=config.name,
                    success=False,
                    passed=0,
                    failed=0, 
                    total=0,
                    duration=time.time() - start_time,
                    error="Server failed to start"
                )
            
            
            # Create test data if newdata mode
            if self.newdata:
                if not await self.create_test_data(config_file):
                    return TestResult(
                        config_name=config.name,
                        success=False,
                        passed=0,
                        failed=0,
                        total=0, 
                        duration=time.time() - start_time,
                        error="Test data creation failed"
                    )
            
            # Run tests using new framework
            orchestrator = ComprehensiveTestOrchestrator(
                f"http://localhost:{self.server_port}", 
                self.verbose, 
                self.curl
            )
            
            # Run selected test suites
            test_suites = []
            test_suites.extend([
                ("Basic API Tests", BasicAPITester),
                ("View Parameter Tests", ViewParameterTester)
            ])
 
            if not self.basic:
                test_suites.extend([
                    ("Pagination Tests", PaginationTester),
                    ("Sorting Tests", SortingTester), 
                    ("Filtering Tests", FilteringTester),
                    ("Combination Tests", CombinationTester),
                ])
            
            total_passed = 0
            total_failed = 0
            total_tests = 0
            
            print(f"  📊 Progress: Starting {len(test_suites)} test suites...")
            
            for test_name, test_class in test_suites:
                if self.verbose:
                    print(f"  🧪 Running {test_name}...")
                else:
                    print(f"  📊 Progress: {total_tests + 1}/{len(test_suites)} - {test_name}")
                
                tester = test_class(config_file, f"http://localhost:{self.server_port}", 
                                  self.verbose, curl_file_handle=self.curl, mode_name=config.name.replace(" ", "_"))
                
                if not await tester.setup_database_connection():
                    print(f"  ❌ Failed to setup database connection for {test_name}")
                    continue
                
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
                    
                finally:
                    await tester.cleanup_database_connection()
                    # Add longer delay to ensure connections are fully cleaned up
                    await asyncio.sleep(3)
                    print(f"  🔄 Cleanup completed for {test_name}")
            
            # No cleanup needed with simplified approach
            
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
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive test runner')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed test output')
    parser.add_argument('--curl', action='store_true',
                       help='Write curl commands to curl.sh')
    parser.add_argument('--mongo', action='store_true',
                       help='Test MongoDB configurations only')
    parser.add_argument('--es', action='store_true', 
                       help='Test Elasticsearch configurations only')
    parser.add_argument('--connection', action='store_true',
                       help='Run connectivity tests only')
    parser.add_argument('--newdata', action='store_true',
                       help='Wipe all data and create fresh test data with known validation issues')
    parser.add_argument('--basic', action='store_true',
                       help='Only run basic API tests')
    parser.add_argument('--wipe', action='store_true',
                       help='DESTRUCTIVE: Wipe all data and exit (must be the only argument)')
    args = parser.parse_args()
    
    dbs = []
    if args.mongo:
        dbs.append("mongodb")
    if args.es:
        dbs.append("elasticsearch")

    runner = ComprehensiveTestRunner(
        verbose=args.verbose,
        curl=args.curl,
        dbs=dbs,
        connection=args.connection,
        newdata=args.newdata,
        wipe=args.wipe,
        basic=args.basic
    )
    
    # handle cases where we don't run any test data
    if args.wipe:
        print("  Only running wipe mode - no tests will be executed")
        for config in runner.test_configs:
            await runner.wipe_all_data(runner.create_config_file(config))
        return
    # Handle connection mode
    if runner.connection:
        print("  Running connectivity test")
        await runner.run_connection_test()
        return

    try:
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
        runner.cleanup()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))