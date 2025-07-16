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
    def __init__(self):
        self.server_port = 5500
        self.server_process = None
        self.temp_configs = []
        
        # Define all test configurations
        self.test_configs = [
            TestConfig(
                name="MongoDB without validation",
                database="mongodb",
                validation="none",
                config_data={
                    "database": "mongodb",
                    "db_uri": "mongodb://localhost:27017",
                    "db_name": "eventMgr",
                    "get_validation": "",
                    "unique_validation": False
                }
            ),
            TestConfig(
                name="MongoDB with validation",
                database="mongodb", 
                validation="get_all",
                config_data={
                    "database": "mongodb",
                    "db_uri": "mongodb://localhost:27017",
                    "db_name": "eventMgr",
                    "get_validation": "get_all",
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
                    "get_validation": "",
                    "unique_validation": False
                }
            ),
            TestConfig(
                name="Elasticsearch with validation",
                database="elasticsearch",
                validation="get_all", 
                config_data={
                    "database": "elasticsearch",
                    "db_uri": "http://localhost:9200",
                    "db_name": "eventMgr",
                    "get_validation": "get_all",
                    "unique_validation": True
                }
            )
        ]
    
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
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=Path(__file__).parent.parent  # Run from project root
            )
            
            # Wait for server to be ready
            for attempt in range(30):
                try:
                    import requests
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        print(f"  ✅ Server started (attempt {attempt + 1})")
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
        """Create temporary config file"""
        filename = "temp_test_config.json"  # Reuse same file
        
        with open(filename, 'w') as f:
            json.dump(config.config_data, f, indent=2)
        
        return filename
    
    def run_test(self, config: TestConfig) -> TestResult:
        """Run test for a single configuration"""
        print(f"\n{'='*80}")
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
            
            # Run tests
            print("🧪 Running tests...")
            test_env = os.environ.copy()
            test_env['PYTHONPATH'] = '.'
            
            result = subprocess.run(
                [sys.executable, "tests/test_user_validation.py", config_file],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=Path(__file__).parent.parent,  # Run from project root
                env=test_env  # Use test environment
            )
            
            # Parse results
            output = result.stdout
            passed = 0
            failed = 0
            total = 0
            
            print(f"  Test exit code: {result.returncode}")
            if result.stderr:
                print(f"  Test stderr: {result.stderr}")
            
            for line in output.split('\n'):
                if "Total tests:" in line:
                    total = int(line.split(":")[1].strip())
                elif "Passed:" in line:
                    passed = int(line.split(":")[1].strip())
                elif "Failed:" in line:
                    failed = int(line.split(":")[1].strip())
            
            success = result.returncode == 0
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
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all test configurations"""
        print("🧪 COMPREHENSIVE TEST SUITE")
        print("=" * 80)
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
            if os.path.exists("temp_test_config.json"):
                os.remove("temp_test_config.json")
        except:
            pass
        
        # Make sure server is stopped
        self.stop_server()

def main():
    runner = ComprehensiveTestRunner()
    
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