#!/usr/bin/env python3
"""
Comprehensive Validation Test Suite

4 Server Passes:
1. MongoDB + GV OFF
2. MongoDB + GV ON  
3. Elasticsearch + GV OFF
4. Elasticsearch + GV ON

Within each pass, tests run from simple to complex.
Each test examines notifications in complete detail.
"""

import sys
import json
import requests
import subprocess
import time
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_data_setup import TestDataCreator

@dataclass
class ServerConfig:
    """Server configuration"""
    database: str  # "mongodb" or "elasticsearch"
    gv_enabled: bool  # get_validation on/off
    
    def get_config_data(self) -> dict:
        return {
            "database": self.database,
            "db_uri": "mongodb://localhost:27017" if self.database == "mongodb" else "http://localhost:9200",
            "db_name": "eventMgr",
            "fk_validation": "multiple" if self.gv_enabled else "",
            "unique_validation": self.gv_enabled
        }
    
    def name(self) -> str:
        gv_status = "GV_ON" if self.gv_enabled else "GV_OFF"
        return f"{self.database.upper()}_{gv_status}"

@dataclass
class TestCase:
    """Individual test case"""
    name: str
    description: str
    url_path: str
    expected_notifications: List[Dict[str, Any]]
    expected_status: int = 200

@dataclass
class NotificationExpectation:
    """Detailed notification expectation"""
    type: str  # "VALIDATION", "DATABASE", etc.
    field_name: Optional[str] = None
    message_contains: Optional[str] = None
    value: Optional[Any] = None

@dataclass
class TestResult:
    config: ServerConfig
    test_case: TestCase
    actual_response: dict
    status_code: int
    success: bool
    details: str
    duration: float

class ComprehensiveValidationTester:
    def __init__(self, server_port: int = 5500):
        self.server_port = server_port
        self.server_process = None
        self.current_config = None
        
        # Test data will be created dynamically
        self.test_data = {}
        self.data_creator = None
    
    def get_server_configs(self) -> List[ServerConfig]:
        """Get all 4 server configurations"""
        return [
            ServerConfig("mongodb", False),     # MongoDB + GV OFF
            ServerConfig("mongodb", True),      # MongoDB + GV ON
            ServerConfig("elasticsearch", False), # Elasticsearch + GV OFF
            ServerConfig("elasticsearch", True)   # Elasticsearch + GV ON
        ]
    
    def get_test_cases_for_config(self, config: ServerConfig) -> List[TestCase]:
        """Get test cases for a specific configuration, ordered simple to complex"""
        
        if not self.test_data:
            raise ValueError("Test data not initialized. Call setup_test_data() first.")
        
        # Use test users with specific validation issues
        bad_enum_user = self.test_data["bad_enum"]
        bad_currency_user = self.test_data["bad_currency"] 
        bad_fk_user = self.test_data["bad_fk"]
        multiple_errors_user = self.test_data["multiple_errors"]
        
        base_cases = [
            # 1. Simple field validation tests
            TestCase(
                name="enum_validation",
                description="Test bad enum value in gender field",
                url_path=f"/api/user/{bad_enum_user}",
                expected_notifications=[
                    {
                        "type": "VALIDATION",
                        "field_name": "gender", 
                        "message_contains": "male or female",
                        "description": "Gender enum validation should always work"
                    }
                ]
            ),
            
            TestCase(
                name="currency_validation", 
                description="Test negative netWorth value",
                url_path=f"/api/user/{bad_currency_user}",
                expected_notifications=[
                    {
                        "type": "VALIDATION",
                        "field_name": "netWorth",
                        "message_contains": "greater than or equal to 0",
                        "description": "Currency validation should always work"
                    }
                ]
            ),
            
            # 2. FK validation (depends on GV setting)
            TestCase(
                name="fk_validation_no_view",
                description="Test bad FK without view parameter",
                url_path=f"/api/user/{bad_fk_user}",
                expected_notifications=[
                    {
                        "type": "VALIDATION", 
                        "field_name": "accountId",
                        "message_contains": "does not exist",
                        "description": f"FK validation should {'work' if config.gv_enabled else 'NOT work'} with GV={'ON' if config.gv_enabled else 'OFF'}"
                    }
                ] if config.gv_enabled else []
            ),
            
            # 3. FK validation with view parameter
            TestCase(
                name="fk_validation_with_view",
                description="Test bad FK with view parameter",
                url_path=f"/api/user/{bad_fk_user}?view=%7B%22account%22%3A%5B%22id%22%5D%7D",
                expected_notifications=[
                    {
                        "type": "VALIDATION",
                        "field_name": "accountId", 
                        "message_contains": "does not exist",
                        "description": "FK validation should work with view parameter regardless of GV setting"
                    }
                ]
            ),
            
            # 4. PFS request with validation
            TestCase(
                name="enum_validation_pfs",
                description="Test bad enum with pagination parameters",
                url_path=f"/api/user/{bad_enum_user}?page=1&pageSize=5&sort=username&order=asc",
                expected_notifications=[
                    {
                        "type": "VALIDATION",
                        "field_name": "gender",
                        "message_contains": "male or female", 
                        "description": "Enum validation should work with PFS parameters"
                    }
                ]
            ),
            
            # 5. Complex: PFS + view + validation
            TestCase(
                name="fk_validation_pfs_view",
                description="Test bad FK with both PFS and view parameters",
                url_path=f"/api/user/{bad_fk_user}?view=%7B%22account%22%3A%5B%22id%22%5D%7D&page=1&pageSize=3&sort=createdAt&order=desc",
                expected_notifications=[
                    {
                        "type": "VALIDATION",
                        "field_name": "accountId",
                        "message_contains": "does not exist",
                        "description": "FK validation should work with view+PFS parameters"
                    }
                ]
            ),
            
            # 6. Multiple validation errors
            TestCase(
                name="multiple_validations",
                description="Test multiple validation errors in single user",
                url_path=f"/api/user/{multiple_errors_user}?view=%7B%22account%22%3A%5B%22id%22%5D%7D",
                expected_notifications=[
                    {
                        "type": "VALIDATION",
                        "field_name": "gender",
                        "message_contains": "male or female",
                        "description": "Gender validation error"
                    },
                    {
                        "type": "VALIDATION",
                        "field_name": "netWorth", 
                        "message_contains": "greater than or equal to 0",
                        "description": "Currency validation error"
                    },
                    {
                        "type": "VALIDATION",
                        "field_name": "accountId",
                        "message_contains": "does not exist", 
                        "description": "FK validation error"
                    }
                ]
            )
        ]
        
        return base_cases
    
    async def setup_test_data(self, config_file: str = "tests/temp_test_config.json"):
        """Setup test data for validation testing"""
        print("🧪 Setting up test data...")
        
        self.data_creator = TestDataCreator()
        await self.data_creator.setup_database(config_file)
        self.test_data = await self.data_creator.create_comprehensive_test_data()
        
        print("✅ Test data setup complete")
    
    async def cleanup_test_data(self):
        """Clean up test data"""
        if self.data_creator:
            print("🧹 Cleaning up test data...")
            await self.data_creator.cleanup_test_data()
            await self.data_creator.cleanup_database()
            self.data_creator = None
            self.test_data = {}
            print("✅ Test data cleanup complete")
    
    def start_server(self, config: ServerConfig) -> bool:
        """Start server with specific configuration"""
        if self.current_config and self.current_config.name() == config.name():
            return True  # Already running correct config
        
        print(f"\n🚀 Starting server: {config.name()}")
        
        # Stop current server
        self.cleanup_server()
        
        # Create config file
        config_data = config.get_config_data()
        config_file = f"temp_comprehensive_config.json"
        
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
            for attempt in range(25):
                try:
                    response = requests.get(f"http://localhost:{self.server_port}/api/metadata", timeout=2)
                    if response.status_code == 200:
                        print(f"   ✅ Server ready (attempt {attempt + 1})")
                        self.current_config = config
                        return True
                except:
                    pass
                time.sleep(1)
            
            print("   ❌ Server failed to start")
            if self.server_process:
                try:
                    stdout, stderr = self.server_process.communicate(timeout=2)
                    if stderr:
                        print(f"   📋 Server stderr: {stderr}")
                    if stdout:
                        print(f"   📋 Server stdout: {stdout}")
                except:
                    print("   ⚠️  Could not get server output")
            return False
            
        except Exception as e:
            print(f"   ❌ Server start error: {e}")
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
        
        # Kill lingering processes
        try:
            subprocess.run(["pkill", "-f", "main.py"], capture_output=True, text=True)
        except Exception:
            pass
        
        time.sleep(0.5)
        
        # Clean up config file
        try:
            Path("temp_comprehensive_config.json").unlink(missing_ok=True)
        except:
            pass
    
    def validate_notifications(self, actual_notifications: List[Dict], expected_notifications: List[Dict]) -> tuple[bool, str]:
        """Validate notifications match expectations exactly"""
        
        if not expected_notifications:
            # Expect no notifications
            if not actual_notifications:
                return True, "Correctly no notifications"
            else:
                return False, f"Expected no notifications but got {len(actual_notifications)}: {actual_notifications}"
        
        if not actual_notifications:
            return False, f"Expected {len(expected_notifications)} notifications but got none"
        
        validation_details = []
        
        for expected in expected_notifications:
            # Find matching notification
            matching_notifications = []
            
            for actual in actual_notifications:
                # Check type match
                if actual.get('type') != expected.get('type'):
                    continue
                
                # Check field name match if specified
                if 'field_name' in expected:
                    if actual.get('field_name') != expected.get('field_name'):
                        continue
                
                # Check message contains if specified
                if 'message_contains' in expected:
                    actual_message = actual.get('message', '').lower()
                    expected_phrase = expected.get('message_contains', '').lower()
                    if expected_phrase not in actual_message:
                        continue
                
                matching_notifications.append(actual)
            
            if not matching_notifications:
                expected_desc = expected.get('description', 'Unknown expectation')
                return False, f"Missing expected notification: {expected_desc}. Expected: {expected}. Actual notifications: {actual_notifications}"
            
            # Found match
            match = matching_notifications[0]
            validation_details.append(f"✅ Found {expected['type']} for {expected.get('field_name', 'field')}: {match.get('message', 'No message')}")
        
        return True, "; ".join(validation_details)
    
    def run_test_case(self, config: ServerConfig, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        start_time = time.time()
        
        try:
            # Make API request
            url = f"http://localhost:{self.server_port}{test_case.url_path}"
            
            response = requests.get(url, timeout=10)
            response_data = response.json()
            
            # Extract notifications
            actual_notifications = response_data.get('notifications', [])
            
            # Validate notifications
            success, details = self.validate_notifications(actual_notifications, test_case.expected_notifications)
            
            return TestResult(
                config=config,
                test_case=test_case,
                actual_response=response_data,
                status_code=response.status_code,
                success=success,
                details=details,
                duration=time.time() - start_time
            )
            
        except Exception as e:
            return TestResult(
                config=config,
                test_case=test_case,
                actual_response={},
                status_code=0,
                success=False,
                details=f"Request failed: {str(e)}",
                duration=time.time() - start_time
            )
    
    async def run_configuration_pass(self, config: ServerConfig) -> List[TestResult]:
        """Run all tests for a single server configuration"""
        print(f"\n{'='*80}")
        print(f"PASS: {config.name()}")
        print(f"Database: {config.database}")
        print(f"GV Setting: {'ON' if config.gv_enabled else 'OFF'}")
        print('='*80)
        
        # Start server for this configuration
        if not self.start_server(config):
            print("❌ Failed to start server - skipping all tests for this configuration")
            return []
        
        # Setup test data for this configuration
        await self.setup_test_data("tests/temp_test_config.json")
        
        try:
            # Get test cases for this configuration
            test_cases = self.get_test_cases_for_config(config)
            results = []
            
            print(f"Running {len(test_cases)} test cases (simple → complex)...")
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n[{i}/{len(test_cases)}] {test_case.name}")
                print(f"   Description: {test_case.description}")
                print(f"   URL: {test_case.url_path}")
                
                result = self.run_test_case(config, test_case)
                results.append(result)
                
                # Show detailed result
                status = "✅ PASS" if result.success else "❌ FAIL"
                print(f"   {status} ({result.duration:.1f}s)")
                print(f"   Details: {result.details}")
                
                if not result.success:
                    print(f"   Expected: {test_case.expected_notifications}")
                    print(f"   Actual notifications: {result.actual_response.get('notifications', [])}")
            
            # Show pass summary
            passed = sum(1 for r in results if r.success)
            print(f"\n📊 Pass Summary: {passed}/{len(results)} tests passed")
            
            return results
            
        finally:
            # Always clean up test data after each configuration
            await self.cleanup_test_data()
    
    async def run_comprehensive_tests(self) -> List[TestResult]:
        """Run all 4 configuration passes"""
        all_results = []
        configs = self.get_server_configs()
        
        print("🧪 COMPREHENSIVE VALIDATION TEST SUITE")
        print("=" * 80)
        print("Running 4 server configuration passes:")
        print("1. MongoDB + GV OFF")
        print("2. MongoDB + GV ON") 
        print("3. Elasticsearch + GV OFF")
        print("4. Elasticsearch + GV ON")
        print("=" * 80)
        
        try:
            for i, config in enumerate(configs, 1):
                print(f"\n🔄 Starting Pass {i}/4: {config.name()}")
                
                config_results = await self.run_configuration_pass(config)
                all_results.extend(config_results)
                
                print(f"✅ Completed Pass {i}/4")
        
        finally:
            self.cleanup_server()
            # Final cleanup in case any test data remains
            await self.cleanup_test_data()
        
        return all_results
    
    def print_final_summary(self, results: List[TestResult]):
        """Print comprehensive final summary"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE VALIDATION TEST RESULTS")
        print('='*80)
        
        total = len(results)
        passed = sum(1 for r in results if r.success)
        failed = total - passed
        
        print(f"Total test cases: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        if total > 0:
            print(f"Overall success rate: {(passed/total)*100:.1f}%")
        else:
            print("No tests were run")
        print()
        
        # Results by configuration
        by_config = {}
        for result in results:
            config_name = result.config.name()
            if config_name not in by_config:
                by_config[config_name] = {"passed": 0, "total": 0}
            by_config[config_name]["total"] += 1
            if result.success:
                by_config[config_name]["passed"] += 1
        
        print("Results by Configuration:")
        for config_name, stats in by_config.items():
            success_rate = (stats['passed']/stats['total'])*100
            print(f"  {config_name}: {stats['passed']}/{stats['total']} ({success_rate:.1f}%)")
        
        # Failed test details
        failed_results = [r for r in results if not r.success]
        if failed_results:
            print(f"\nFailed Test Cases:")
            for result in failed_results:
                print(f"  ❌ {result.config.name()}::{result.test_case.name}")
                print(f"     {result.details}")
        else:
            print(f"\n🎉 ALL TESTS PASSED!")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Comprehensive Validation Test Suite')
    parser.add_argument('--config', choices=['mongo-off', 'mongo-on', 'es-off', 'es-on'],
                       help='Run only specific configuration')
    args = parser.parse_args()
    
    tester = ComprehensiveValidationTester()
    
    try:
        if args.config:
            # Run specific configuration only
            config_map = {
                'mongo-off': ServerConfig("mongodb", False),
                'mongo-on': ServerConfig("mongodb", True), 
                'es-off': ServerConfig("elasticsearch", False),
                'es-on': ServerConfig("elasticsearch", True)
            }
            config = config_map[args.config]
            results = await tester.run_configuration_pass(config)
        else:
            # Run all configurations
            results = await tester.run_comprehensive_tests()
        
        tester.print_final_summary(results)
        
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
        await tester.cleanup_test_data()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))