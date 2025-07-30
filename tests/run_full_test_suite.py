#!/usr/bin/env python3
"""
Comprehensive test wrapper that runs all database/validation combinations.

This script:
1. Tests both MongoDB and Elasticsearch
2. Tests both with and without fk_validation
3. Starts/stops the server between each run
4. Provides comprehensive reporting
"""

import sys
import os
import subprocess
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class TestConfiguration:
    """Configuration for a single test run"""
    database: str
    validation: str
    config_file: str
    description: str

@dataclass
class TestResult:
    """Result from a single test run"""
    config: TestConfiguration
    passed: int
    failed: int
    total: int
    duration: float
    success: bool
    error_message: Optional[str] = None

class FullTestSuite:
    """Manages full test suite execution across all configurations"""
    
    def __init__(self, server_script: str = "app/main.py", server_port: int = 5500):
        self.server_script = server_script
        self.server_port = server_port
        self.server_process = None
        self.results: List[TestResult] = []
        
        # Define test configurations
        self.configurations = [
            TestConfiguration(
                database="mongodb",
                validation="none",
                config_file="mongo.json",
                description="MongoDB without validation"
            ),
            TestConfiguration(
                database="mongodb", 
                validation="get_all",
                config_file="mongo_validation.json",
                description="MongoDB with get_all validation"
            ),
            TestConfiguration(
                database="elasticsearch",
                validation="none", 
                config_file="es.json",
                description="Elasticsearch without validation"
            ),
            TestConfiguration(
                database="elasticsearch",
                validation="get_all",
                config_file="es_validation.json", 
                description="Elasticsearch with get_all validation"
            )
        ]
    
    def create_config_files(self):
        """Create temporary config files for validation tests"""
        print("📁 Creating configuration files...")
        
        # Base configurations
        configs = {
            "mongo.json": {
                "database": "mongodb",
                "db_uri": "mongodb://localhost:27017", 
                "db_name": "eventMgr",
                "fk_validation": "",
                "unique_validation": False
            },
            "mongo_validation.json": {
                "database": "mongodb",
                "db_uri": "mongodb://localhost:27017",
                "db_name": "eventMgr", 
                "fk_validation": "multiple",
                "unique_validation": True
            },
            "es.json": {
                "database": "elasticsearch",
                "db_uri": "http://localhost:9200",
                "db_name": "eventMgr",
                "fk_validation": "",
                "unique_validation": False
            },
            "es_validation.json": {
                "database": "elasticsearch",
                "db_uri": "http://localhost:9200", 
                "db_name": "eventMgr",
                "fk_validation": "multiple",
                "unique_validation": True
            }
        }
        
        # Write config files
        for filename, config in configs.items():
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"  ✅ Created {filename}")
    
    def start_server(self, config_file: str) -> bool:
        """Start the server with specified configuration"""
        print(f"🚀 Starting server with {config_file}...")
        
        try:
            # Kill any existing server processes first
            self.kill_existing_servers()
            
            # Start server process in background
            env = os.environ.copy()
            env['CONFIG_FILE'] = config_file
            
            self.server_process = subprocess.Popen(
                [sys.executable, self.server_script],
                env=env,
                stdout=subprocess.DEVNULL,  # Don't capture output to avoid blocking
                stderr=subprocess.DEVNULL,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Create new process group
            )
            
            # Wait for server to start
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    import requests
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        print(f"  ✅ Server started successfully (attempt {attempt + 1})")
                        return True
                except:
                    pass
                time.sleep(1)
            
            print(f"  ❌ Server failed to start after {max_attempts} attempts")
            return False
            
        except Exception as e:
            print(f"  ❌ Failed to start server: {e}")
            return False
    
    def kill_existing_servers(self):
        """Kill any existing server processes on the port"""
        try:
            # Try to find and kill processes using our port
            result = subprocess.run(
                ["lsof", "-ti", f":{self.server_port}"],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        try:
                            subprocess.run(["kill", "-9", pid.strip()], check=False)
                            print(f"  🔪 Killed existing process {pid.strip()}")
                        except:
                            pass
                time.sleep(1)
        except:
            pass  # lsof might not be available
    
    def stop_server(self):
        """Stop the server"""
        if self.server_process:
            print("🛑 Stopping server...")
            try:
                # Try graceful termination first
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                    print("  ✅ Server stopped gracefully")
                except subprocess.TimeoutExpired:
                    print("  ⚠️  Server didn't stop gracefully, force killing...")
                    
                    # Force kill the process group
                    if hasattr(os, 'killpg'):
                        try:
                            os.killpg(os.getpgid(self.server_process.pid), 9)
                        except:
                            pass
                    
                    # Force kill the process
                    self.server_process.kill()
                    self.server_process.wait()
                    print("  ✅ Server force killed")
                    
            except Exception as e:
                print(f"  ⚠️  Error stopping server: {e}")
            
            self.server_process = None
        
        # Kill any remaining processes on the port
        self.kill_existing_servers()
        
        # Wait for port to be released
        time.sleep(3)
    
    def run_test_configuration(self, config: TestConfiguration) -> TestResult:
        """Run tests for a single configuration"""
        print(f"\n{'='*80}")
        print(f"TESTING: {config.description}")
        print(f"Database: {config.database}")
        print(f"Validation: {config.validation}")
        print(f"Config file: {config.config_file}")
        print('='*80)
        
        start_time = time.time()
        
        try:
            # Start server with this configuration
            if not self.start_server(config.config_file):
                return TestResult(
                    config=config,
                    passed=0,
                    failed=0,
                    total=0,
                    duration=time.time() - start_time,
                    success=False,
                    error_message="Failed to start server"
                )
            
            # Run the test suite
            print(f"🧪 Running test suite...")
            result = subprocess.run(
                [sys.executable, "tests/test_user_validation.py", config.config_file],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Parse results from output
            output_lines = result.stdout.split('\n')
            
            # Look for test summary
            passed = 0
            failed = 0
            total = 0
            
            for line in output_lines:
                if "Total tests:" in line:
                    total = int(line.split(":")[1].strip())
                elif "Passed:" in line:
                    passed = int(line.split(":")[1].strip())
                elif "Failed:" in line:
                    failed = int(line.split(":")[1].strip())
            
            success = result.returncode == 0
            error_message = None
            
            if not success:
                error_message = result.stderr or "Test execution failed"
            
            duration = time.time() - start_time
            
            return TestResult(
                config=config,
                passed=passed,
                failed=failed,
                total=total,
                duration=duration,
                success=success,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                config=config,
                passed=0,
                failed=0,
                total=0,
                duration=time.time() - start_time,
                success=False,
                error_message="Test execution timed out"
            )
        except Exception as e:
            return TestResult(
                config=config,
                passed=0,
                failed=0,
                total=0,
                duration=time.time() - start_time,
                success=False,
                error_message=str(e)
            )
        finally:
            # Always stop server
            self.stop_server()
    
    def run_all_tests(self) -> bool:
        """Run all test configurations"""
        print("🧪 COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print("Testing all database and validation combinations...")
        print(f"Configurations: {len(self.configurations)}")
        print()
        
        # Create config files
        self.create_config_files()
        
        # Run each configuration
        for config in self.configurations:
            result = self.run_test_configuration(config)
            self.results.append(result)
            
            # Print immediate result
            if result.success:
                print(f"✅ {config.description}: {result.passed}/{result.total} tests passed")
            else:
                print(f"❌ {config.description}: FAILED - {result.error_message}")
        
        # Print comprehensive summary
        self.print_summary()
        
        # Return overall success
        return all(result.success for result in self.results)
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE TEST SUMMARY")
        print('='*80)
        
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_tests = sum(r.total for r in self.results)
        total_duration = sum(r.duration for r in self.results)
        successful_configs = sum(1 for r in self.results if r.success)
        
        print(f"Configurations tested: {len(self.results)}")
        print(f"Successful configurations: {successful_configs}/{len(self.results)}")
        print(f"Total tests run: {total_tests}")
        print(f"Total tests passed: {total_passed}")
        print(f"Total tests failed: {total_failed}")
        print(f"Overall success rate: {(total_passed/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
        print(f"Total duration: {total_duration:.2f}s")
        
        print(f"\n📊 DETAILED RESULTS:")
        print("-" * 80)
        
        for result in self.results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"{status} {result.config.description}")
            print(f"     Tests: {result.passed}/{result.total} passed ({result.duration:.2f}s)")
            if result.error_message:
                print(f"     Error: {result.error_message}")
            print()
        
        if not all(result.success for result in self.results):
            print("❌ FAILED CONFIGURATIONS:")
            for result in self.results:
                if not result.success:
                    print(f"  - {result.config.description}: {result.error_message}")
        
        print(f"\n{'='*80}")
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            config_files = ["mongo_validation.json", "es_validation.json"]
            for file in config_files:
                if os.path.exists(file):
                    os.remove(file)
                    print(f"🧹 Cleaned up {file}")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

def main():
    """Main execution function"""
    print("🚀 Starting Comprehensive Test Suite")
    print("This will test all database and validation combinations")
    print()
    
    suite = FullTestSuite()
    
    try:
        success = suite.run_all_tests()
        
        if success:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("💥 SOME TESTS FAILED!")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test suite interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test suite failed with exception: {e}")
        return 1
    finally:
        # Always cleanup
        suite.stop_server()
        suite.cleanup()

if __name__ == "__main__":
    sys.exit(main())