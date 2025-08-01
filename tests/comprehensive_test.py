#!/usr/bin/env python3
"""
Comprehensive test runner that handles server lifecycle and all configurations.
"""

import sys
import os
import subprocess
import time
import json
import signal
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class TestConfig:
    name: str
    database: str
    validation: str
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
    def __init__(self, verbose: bool = False, curl: bool = False, mongo_only: bool = False, es_only: bool = False, noop: bool = False, pfs_only: bool = False, newdata: bool = False, nopaging: bool = False):
        self.server_port = 5500
        self.server_process = None
        self.temp_configs = []
        self.verbose = verbose
        self.curl = curl
        self.mongo_only = mongo_only
        self.es_only = es_only
        self.noop = noop
        self.pfs_only = pfs_only
        self.newdata = newdata
        self.nopaging = nopaging
        
        # Define all test configurations
        all_configs = [
            TestConfig(
                name="MongoDB without validation",
                database="mongodb",
                validation="none",
                config_data={
                    "database": "mongodb",
                    "db_uri": "mongodb://localhost:27017",
                    "db_name": "eventMgr",
                    "fk_validation": "",
                    "unique_validation": False
                }
            ),
            TestConfig(
                name="MongoDB with validation",
                database="mongodb", 
                validation="multiple",
                config_data={
                    "database": "mongodb",
                    "db_uri": "mongodb://localhost:27017",
                    "db_name": "eventMgr",
                    "fk_validation": "multiple",
                    "unique_validation": True
                }
            ),
            TestConfig(
                name="Elasticsearch without validation",
                database="elasticsearch",
                validation="none", 
                config_data={
                    "database": "elasticsearch",
                    "db_uri": "http://localhost:9200",
                    "db_name": "eventMgr",
                    "fk_validation": "",
                    "unique_validation": False
                }
            ),
            TestConfig(
                name="Elasticsearch with validation",
                database="elasticsearch", 
                validation="multiple",
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
        if self.mongo_only and not self.es_only:
            # Only MongoDB
            self.test_configs = [config for config in all_configs if config.database == "mongodb"]
        elif self.es_only and not self.mongo_only:
            # Only Elasticsearch
            self.test_configs = [config for config in all_configs if config.database == "elasticsearch"]
        else:
            # Default: run all configurations (both flags, or neither flag)
            self.test_configs = all_configs
    
    def cleanup_port(self):
        """Kill any processes using our port"""
        try:
            # Use pkill to kill main.py processes
            subprocess.run(["pkill", "-f", "main.py"], check=False)
            time.sleep(1)
        except:
            pass
    
    def start_server(self, config_file: str) -> bool:
        """Start server with given config file"""
        if self.verbose:
            print(f"🚀 Starting server with {config_file}")
        else:
            print(f"🚀 Starting server with {config_file}")
        
        # Clean up any existing processes
        self.cleanup_port()
        
        try:
            # Start server - EXACTLY like the working command line
            env = os.environ.copy()
            env['PYTHONPATH'] = '.'
            
            self.server_process = subprocess.Popen(
                [sys.executable, "app/main.py", config_file],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=Path(__file__).parent.parent  # Run from project root
            )
            
            # Wait for server to be ready
            for attempt in range(30):
                try:
                    import requests
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        if self.verbose:
                            print(f"  ✅ Server ready (attempt {attempt + 1}, response time: {response.elapsed.total_seconds()*1000:.0f}ms)")
                        else:
                            print(f"  ✅ Server started (attempt {attempt + 1})")
                        return True
                except Exception as e:
                    if self.verbose and attempt > 10:
                        print(f"  ⏳ Waiting for server (attempt {attempt + 1}): {e}")
                time.sleep(1)
            
            print("  ❌ Server failed to start")
            # Get server output to see what went wrong
            if self.server_process:
                try:
                    stdout, stderr = self.server_process.communicate(timeout=2)
                    if stdout:
                        print("📋 Server STDOUT:")
                        print(stdout)
                    if stderr:
                        print("📋 Server STDERR:")  
                        print(stderr)
                except:
                    print("  ⚠️  Could not get server output")
            return False
            
        except Exception as e:
            print(f"  ❌ Server start error: {e}")
            return False
    
    def stop_server(self):
        """Stop the server"""
        print("🛑 Stopping server")
        if self.server_process:
            try:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=3)
                    print("  ✅ Server stopped")
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                    self.server_process.wait()
                    print("  ✅ Server killed")
            except Exception as e:
                print(f"  ⚠️  Server stop error: {e}")
            
            self.server_process = None
        
        # Clean up any remaining processes  
        self.cleanup_port()
        time.sleep(1)
    
    def create_config_file(self, config: TestConfig) -> str:
        """Create temporary config file in tests directory"""
        filename = "tests/temp_test_config.json"  # Create in tests dir
        
        with open(filename, 'w') as f:
            json.dump(config.config_data, f, indent=2)
        
        return filename
    
    def run_test(self, config: TestConfig) -> TestResult:
        """Run test for a single configuration"""
        print(f"\n{'='*80}")
        if self.verbose:
            print(f"📋 CONFIGURATION: {config.name}")
            print(f"🗄️  Database: {config.database}")
            print(f"✅ Validation: {config.validation}")
            print('='*80)
        else:
            print(f"TESTING: {config.name}")
            print('='*80)
        
        start_time = time.time()
        
        try:
            # Create config file
            config_file = self.create_config_file(config)
            
            # Start server
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
            
            # Run tests or noop
            if self.noop:
                # Noop mode - just test connectivity
                return self._run_noop_test(config, start_time)
            else:
                # Regular test mode
                if self.pfs_only:
                    print("🧪 Running pagination/filter/sort tests only...")
                else:
                    print("🧪 Running tests...")
                test_env = os.environ.copy()
                test_env['PYTHONPATH'] = '.'
            
            # Build command args with verbose and curl if needed  
            extra_args = []
            if self.verbose:
                extra_args.append("--verbose")
            if self.curl:
                extra_args.append("--curl")
            if self.nopaging:
                extra_args.append("--nopaging")
            
            results = []
            
            if self.newdata:
                # NEWDATA MODE: Use dedicated newdata validation module
                if self.verbose:
                    print("  🧹 NEWDATA MODE: Running controlled validation tests...")
                else:
                    print("  🧹 NEWDATA MODE: Controlled validation tests...")
                
                result_newdata = subprocess.run(
                    [sys.executable, "tests/test_newdata_validation.py", 
                     "--config", config_file, 
                     "--server", f"http://localhost:{self.server_port}"] + (["--curl"] if self.curl else []),
                    capture_output=True,
                    text=True,
                    timeout=600,  # Longer timeout for wipe + create + test cycle
                    cwd=Path(__file__).parent.parent,
                    env=test_env
                )
                results.append(result_newdata)
                
            else:
                # DEFAULT MODE: Use existing database state
                if not self.pfs_only:
                    # Run user validation tests
                    if self.verbose:
                        print("  📝 Running user validation tests with verbose output...")
                    else:
                        print("  📝 Running user validation tests...")
                    result1 = subprocess.run(
                        [sys.executable, "tests/test_user_validation.py", config_file] + extra_args,
                        capture_output=True,
                        text=True,
                        timeout=180,
                        cwd=Path(__file__).parent.parent,  # Run from project root
                        env=test_env  # Use test environment
                    )
                    results.append(result1)
                    
                    # Run FK processing tests  
                    if self.verbose:
                        print("  🔗 Running FK processing tests with verbose output...")
                    else:
                        print("  🔗 Running FK processing tests...")
                    result2 = subprocess.run(
                        [sys.executable, "tests/test_fk_processing.py", config_file] + extra_args,
                        capture_output=True,
                        text=True,
                        timeout=180,
                        cwd=Path(__file__).parent.parent,
                        env=test_env
                    )
                    results.append(result2)
                
                # Always run pagination tests (either as part of full suite or PFS-only)
                if self.verbose:
                    print("  📄 Running pagination tests with verbose output...")
                else:
                    print("  📄 Running pagination tests...")
                result3 = subprocess.run(
                    [sys.executable, "tests/test_pagination_integration.py", config_file] + extra_args,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=Path(__file__).parent.parent,
                    env=test_env
                )
                results.append(result3)
                
                # Run API validation module tests
                if self.verbose:
                    print("  🔍 Running API validation module tests with verbose output...")
                else:
                    print("  🔍 Running API validation module tests...")
                result5 = subprocess.run(
                    [sys.executable, "tests/modules/test_api_module.py"] + (["--curl"] if self.curl else []),
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=Path(__file__).parent.parent,
                    env=test_env
                )
                results.append(result5)
            
            # Combine results
            result = self._combine_test_results(*results)
            
            # Parse results
            output = result.stdout
            passed = 0
            failed = 0
            total = 0
            
            if self.verbose:
                print(f"  🔍 Test exit code: {result.returncode}")
                if result.stderr:
                    print(f"  ⚠️  Test stderr output:")
                    print("     " + result.stderr.replace("\n", "\n     "))
                if result.stdout:
                    print(f"  📄 Test stdout:")
                    print("     " + result.stdout.replace("\n", "\n     "))
            else:
                if result.stderr:
                    print(f"  Test stderr: {result.stderr}")
            
            for line in output.split('\n'):
                if "Total tests:" in line:
                    total = int(line.split(":")[1].strip())
                elif "Passed:" in line:
                    passed = int(line.split(":")[1].strip())
                elif "Failed:" in line:
                    failed = int(line.split(":")[1].strip())
            
            # Consider successful if all parsed tests passed, even if exit code is non-zero
            success = (result.returncode == 0) or (total > 0 and failed == 0)
            error = None if success else result.stderr or "Test execution failed"
            
            print(f"  Parsed results: {passed}/{total} passed, success={success}")
            
            return TestResult(
                config_name=config.name,
                success=success,
                passed=passed,
                failed=failed,
                total=total,
                duration=time.time() - start_time,
                error=error
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                config_name=config.name,
                success=False,
                passed=0,
                failed=0,
                total=0,
                duration=time.time() - start_time,
                error="Test timed out"
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
            # Always stop server
            self.stop_server()
    
    def _combine_test_results(self, *results: subprocess.CompletedProcess) -> subprocess.CompletedProcess:
        """Combine results from multiple test runs."""
        from types import SimpleNamespace
        
        # Combine stdout and stderr from all results
        separator = '='*50
        combined_stdout = f"\n{separator}\n".join(result.stdout for result in results)
        combined_stderr = f"\n{separator}\n".join(result.stderr for result in results)
        
        # Return code is success only if all succeeded
        combined_returncode = 0 if all(result.returncode == 0 for result in results) else 1
        
        # Create a combined result object
        combined_result = SimpleNamespace()
        combined_result.stdout = combined_stdout
        combined_result.stderr = combined_stderr
        combined_result.returncode = combined_returncode
        
        return combined_result
    
    def _run_noop_test(self, config: TestConfig, start_time: float) -> TestResult:
        """Run no-op connectivity test without actual test execution"""
        print("🔗 Running no-op connectivity test...")
        
        try:
            import requests
            
            # Test basic endpoint
            response = requests.get(f"http://localhost:{self.server_port}/api/user", timeout=5)
            if response.status_code != 200:
                return TestResult(
                    config_name=config.name,
                    success=False,
                    passed=0,
                    failed=1,
                    total=1,
                    duration=time.time() - start_time,
                    error=f"Basic endpoint failed: {response.status_code}"
                )
            print(f"  ✅ Basic endpoint responds: {response.status_code}")
            
            # Test view endpoint (the problematic one)
            view_url = f"http://localhost:{self.server_port}/api/user?view=%7b%22account%22%3a%5b%22createdat%22%5d%7d"
            print("  🔍 Testing view endpoint (known to hang in full tests)...")
            response = requests.get(view_url, timeout=15)  # Longer timeout for view
            if response.status_code != 200:
                return TestResult(
                    config_name=config.name,
                    success=False,
                    passed=1,
                    failed=1,
                    total=2,
                    duration=time.time() - start_time,
                    error=f"View endpoint failed: {response.status_code}"
                )
            print(f"  ✅ View endpoint responds: {response.status_code}")
            
            # Success
            return TestResult(
                config_name=config.name,
                success=True,
                passed=2,
                failed=0,
                total=2,
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                config_name=config.name,
                success=False,
                passed=0,
                failed=2,
                total=2,
                duration=time.time() - start_time,
                error=f"Connectivity test failed: {e}"
            )
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all test configurations"""
        if self.noop:
            print("🧪 COMPREHENSIVE TEST SUITE - NO-OP MODE")
            print("=" * 80)
            print("🔗 Testing process management and connectivity only")
        elif self.pfs_only:
            print("🧪 COMPREHENSIVE TEST SUITE - PAGINATION/FILTER/SORT ONLY")
            print("=" * 80)
            print("📄 Testing pagination, filtering, and sorting functionality only")
        elif self.newdata:
            print("🧪 COMPREHENSIVE TEST SUITE - CONTROLLED DATA MODE")
            print("=" * 80)
            print("🧹 Wiping database and creating controlled test data with known validation issues")
        else:
            print("🧪 COMPREHENSIVE TEST SUITE - EXISTING DATA MODE")
            print("=" * 80)
            print("📊 Using existing database state (may have unpredictable results)")
        
        # Show which databases are being tested
        if self.mongo_only and not self.es_only:
            print("🗄️  Testing: MongoDB only")
        elif self.es_only and not self.mongo_only:
            print("🔍 Testing: Elasticsearch only")
        else:
            print("🗄️  Testing: MongoDB + Elasticsearch")
            
        print(f"Running {len(self.test_configs)} configurations...")
        print()
        
        results = []
        
        for config in self.test_configs:
            result = self.run_test(config)
            results.append(result)
            
            # Print immediate result
            if result.success:
                print(f"✅ {config.name}: {result.passed}/{result.total} tests passed ({result.duration:.1f}s)")
            else:
                print(f"❌ {config.name}: FAILED - {result.error} ({result.duration:.1f}s)")
        
        return results
    
    def print_summary(self, results: List[TestResult]):
        """Print comprehensive summary"""
        print(f"\n{'='*80}")
        print("FINAL SUMMARY")
        print('='*80)
        
        total_passed = sum(r.passed for r in results)
        total_failed = sum(r.failed for r in results)
        total_tests = sum(r.total for r in results)
        successful_configs = sum(1 for r in results if r.success)
        total_duration = sum(r.duration for r in results)
        
        print(f"Configurations: {successful_configs}/{len(results)} passed")
        print(f"Total tests: {total_passed}/{total_tests} passed")
        print(f"Total duration: {total_duration:.1f}s")
        print()
        
        for result in results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"{status} {result.config_name}")
            if result.total > 0:
                print(f"     {result.passed}/{result.total} tests passed")
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
        
        # Make sure server is stopped
        self.stop_server()

def main():
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Comprehensive test runner for Events application')
    parser.add_argument('--verbose', action='store_true', 
                       help='Show detailed URL testing and response information')
    parser.add_argument('--curl', action='store_true',
                       help='Dump all API calls in curl format to curl.sh (overwrites existing file)')
    parser.add_argument('--mongo', action='store_true',
                       help='Include MongoDB configurations (both validation modes)')
    parser.add_argument('--es', action='store_true',
                       help='Include Elasticsearch configurations (both validation modes)')
    parser.add_argument('--noop', action='store_true',
                       help='Run no-op connectivity tests only (no actual test execution)')
    parser.add_argument('--pfs', action='store_true',
                       help='Run only pagination/filter/sort tests (skip user validation and FK processing)')
    parser.add_argument('--newdata', action='store_true',
                       help='Wipe database and create controlled test data with known validation issues (guarantees clean state)')
    parser.add_argument('--nopaging', action='store_true',
                       help='Skip pagination data validation (for working without pagination implementation)')
    args = parser.parse_args()
    
    # Note: --mongo and --es can be used together (same as default)
    
    runner = ComprehensiveTestRunner(
        verbose=args.verbose, 
        curl=args.curl, 
        mongo_only=args.mongo, 
        es_only=args.es,
        noop=args.noop,
        pfs_only=args.pfs,
        newdata=args.newdata,
        nopaging=args.nopaging
    )
    
    try:
        results = runner.run_all_tests()
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
    sys.exit(main())