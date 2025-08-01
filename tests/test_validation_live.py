#!/usr/bin/env python3
"""
Comprehensive Validation Tests Against Live Server

Assumes server is already running (via Docker or otherwise).
Generates comprehensive curl commands for all validation scenarios.
"""

import sys
import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import urllib.parse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_data_setup import TestDataCreator

@dataclass
class TestScenario:
    """Test scenario definition"""
    name: str
    description: str
    url_path: str
    expected_validations: List[str]  # Field names that should have validation errors
    should_have_notifications: bool

class LiveValidationTester:
    def __init__(self, server_url: str = "http://localhost:5500", curl_output: bool = False):
        self.server_url = server_url
        self.curl_output = curl_output
        
        # Test data will be created dynamically
        self.test_data = {}
        self.data_creator = None
        
        if self.curl_output:
            self._init_curl_file()
    
    def _init_curl_file(self):
        """Initialize validation_curl.sh file in tests directory"""
        try:
            with open('tests/validation_curl.sh', 'w') as f:
                f.write('#!/bin/bash\n')
                f.write('# Comprehensive Validation Test Curl Commands\n')
                f.write('# Generated by test_validation_live.py\n')
                f.write('# Run: chmod +x tests/validation_curl.sh && ./tests/validation_curl.sh\n\n')
            print("📁 Initialized tests/validation_curl.sh")
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize tests/validation_curl.sh: {e}")
    
    def _append_to_curl_file(self, method: str, url: str):
        """Append curl command to tests/validation_curl.sh"""
        if not self.curl_output:
            return
            
        try:
            with open('tests/validation_curl.sh', 'a') as f:
                # Show decoded URL in echo statement
                decoded_url = self._decode_url_for_display(url)
                f.write(f'echo "=== {method} {decoded_url} ==="\n')
                f.write(f'curl -X {method} "{url}"\n')
                f.write('echo ""\n\n')
        except Exception as e:
            print(f"⚠️ Warning: Could not write to tests/validation_curl.sh: {e}")
    
    def _decode_url_for_display(self, url: str) -> str:
        """Decode URL parameters for readable display"""
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.query:
                return url
            
            # Parse and decode query parameters
            params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            decoded_params = []
            
            for key, values in params.items():
                for value in values:
                    decoded_value = urllib.parse.unquote(value)
                    decoded_params.append(f"{key}={decoded_value}")
            
            decoded_query = "&".join(decoded_params)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{decoded_query}"
        except:
            return url
    
    def check_server_status(self) -> bool:
        """Check if server is running and accessible"""
        try:
            response = requests.get(f"{self.server_url}/api/metadata", timeout=5)
            if response.status_code == 200:
                metadata = response.json()
                print(f"✅ Server is running")
                print(f"   Database: {metadata.get('database', 'unknown')}")
                return True
            else:
                print(f"⚠️ Server responded with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server is not accessible: {e}")
            return False
    
    async def setup_test_data(self):
        """Create test data for validation testing"""
        print("🧪 Setting up test data for validation tests...")
        
        self.data_creator = TestDataCreator()
        await self.data_creator.setup_database()
        self.test_data = await self.data_creator.create_comprehensive_test_data()
        
        print("✅ Test data setup complete")
    
    async def cleanup_test_data(self):
        """Clean up test data"""
        if self.data_creator:
            await self.data_creator.cleanup_test_data()
            await self.data_creator.cleanup_database()
            self.data_creator = None
            self.test_data = {}
    
    def generate_validation_scenarios(self) -> List[TestScenario]:
        """Generate comprehensive validation test scenarios"""
        
        if not self.test_data:
            raise ValueError("Test data not initialized. Call setup_test_data() first.")
        
        # Use test users with specific validation issues  
        bad_enum_user = self.test_data["bad_enum"]
        bad_currency_user = self.test_data["bad_currency"]
        bad_fk_user = self.test_data["bad_fk"]
        multiple_errors_user = self.test_data["multiple_errors"]
        
        # View parameter for FK processing
        view_param = urllib.parse.quote('{"account":["id"]}')
        
        scenarios = [
            # 1. Basic field validation tests
            TestScenario(
                name="enum_validation_simple",
                description="Test bad enum value (should always show validation error)",
                url_path=f"/api/user/{bad_enum_user}",
                expected_validations=["gender"],
                should_have_notifications=True
            ),
            
            TestScenario(
                name="currency_validation_simple", 
                description="Test negative currency value (should always show validation error)",
                url_path=f"/api/user/{bad_currency_user}",
                expected_validations=["netWorth"],
                should_have_notifications=True
            ),
            
            # 2. FK validation without view (depends on GV setting)
            TestScenario(
                name="fk_validation_no_view",
                description="Test bad FK without view parameter (depends on GV setting)",
                url_path=f"/api/user/{bad_fk_user}",
                expected_validations=["accountId"],
                should_have_notifications=True  # Will depend on server GV setting
            ),
            
            # 3. FK validation with view (should always work)
            TestScenario(
                name="fk_validation_with_view",
                description="Test bad FK with view parameter (should always work)",
                url_path=f"/api/user/{bad_fk_user}?view={view_param}",
                expected_validations=["accountId"],
                should_have_notifications=True
            ),
            
            # 4. Multiple validation errors
            TestScenario(
                name="multiple_validations",
                description="Test multiple validation errors with view",
                url_path=f"/api/user/{multiple_errors_user}?view={view_param}",
                expected_validations=["gender", "netWorth", "accountId"],
                should_have_notifications=True
            ),
            
            # 5. Validation with PFS parameters
            TestScenario(
                name="validation_with_pfs",
                description="Test validation with pagination/filtering/sorting",
                url_path=f"/api/user/{bad_enum_user}?page=1&pageSize=5&sort=username&order=asc",
                expected_validations=["gender"],
                should_have_notifications=True
            ),
            
            # 6. Complex: Validation + View + PFS
            TestScenario(
                name="validation_view_pfs_complex",
                description="Test all validation types with view and PFS parameters",
                url_path=f"/api/user/{multiple_errors_user}?view={view_param}&page=1&pageSize=3&sort=createdAt&order=desc",
                expected_validations=["gender", "netWorth", "accountId"],
                should_have_notifications=True
            ),
            
            # 7. List endpoint with filters that should trigger validation
            TestScenario(
                name="list_validation_filter",
                description="Test list endpoint with user filter",
                url_path=f"/api/user?filter=id:{bad_enum_user}&pageSize=5",
                expected_validations=["gender"],
                should_have_notifications=True
            ),
            
            # 8. List with view and filter
            TestScenario(
                name="list_validation_view_filter",
                description="Test list endpoint with view and filter",
                url_path=f"/api/user?view={view_param}&filter=id:{multiple_errors_user}&pageSize=3",
                expected_validations=["gender", "netWorth", "accountId"],
                should_have_notifications=True
            ),
            
            # 9. Edge case: Complex filter with validation
            TestScenario(
                name="complex_filter_validation",
                description="Test complex filter combinations with validation",
                url_path=f"/api/user?filter=id:{bad_currency_user},gender:male&pageSize=5",
                expected_validations=["netWorth"],
                should_have_notifications=True
            ),
            
            # 10. FK processing intensive
            TestScenario(
                name="fk_intensive_processing",
                description="Test FK processing with complex view specification",
                url_path=f"/api/user/{bad_fk_user}?view={urllib.parse.quote('{\"account\":[\"id\",\"createdAt\",\"updatedAt\"]}')}",
                expected_validations=["accountId"],
                should_have_notifications=True
            )
        ]
        
        return scenarios
    
    def run_validation_test(self, scenario: TestScenario) -> Dict[str, Any]:
        """Run a single validation test scenario"""
        
        url = f"{self.server_url}{scenario.url_path}"
        
        print(f"\n🧪 Testing: {scenario.name}")
        print(f"   Description: {scenario.description}")
        print(f"   URL: {self._decode_url_for_display(url)}")
        
        # Add to curl file
        self._append_to_curl_file("GET", url)
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            duration = time.time() - start_time
            
            print(f"   Status: {response.status_code} ({duration:.1f}s)")
            
            if response.status_code == 200:
                response_data = response.json()
                return self._analyze_validation_response(scenario, response_data)
            else:
                print(f"   ❌ Non-200 response: {response.text}")
                return {
                    "scenario": scenario.name,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
            return {
                "scenario": scenario.name,
                "success": False,
                "error": str(e),
                "response": None
            }
    
    def _analyze_validation_response(self, scenario: TestScenario, response_data: dict) -> Dict[str, Any]:
        """Analyze response for expected validation patterns"""
        
        # Extract notifications
        notifications = response_data.get('notifications')
        
        # Handle null notifications
        if notifications is None:
            print(f"   🚨 CRITICAL BUG: Notifications field is null - notification system broken")
            if scenario.should_have_notifications:
                print(f"   ❌ Expected notifications but found null")
                print(f"   📋 Response keys: {list(response_data.keys())}")
                return {
                    "scenario": scenario.name,
                    "success": False,
                    "error": "CRITICAL BUG: Notifications are null",
                    "expected": scenario.expected_validations,
                    "actual": [],
                    "critical_bug": True
                }
            else:
                print(f"   ✅ Correctly no notifications")
                return {"scenario": scenario.name, "success": True, "details": "No notifications as expected"}
        
        # Handle both list format and entity-grouped dict format
        validation_notifications = []
        found_fields = []
        
        if isinstance(notifications, list):
            # Standard list format
            validation_notifications = [n for n in notifications if n.get('type') in ['VALIDATION', 'validation']]
            for notif in validation_notifications:
                field_name = notif.get('field_name') or notif.get('field')
                if field_name:
                    found_fields.append(field_name)
        elif isinstance(notifications, dict):
            # Entity-grouped dict format
            print(f"   📋 Notifications in entity-grouped format")
            for entity_id, entity_data in notifications.items():
                if isinstance(entity_data, dict):
                    warnings = entity_data.get('warnings', [])
                    errors = entity_data.get('errors', [])
                    for warning in warnings:
                        if warning.get('type') == 'validation':
                            field_name = warning.get('field')
                            if field_name:
                                found_fields.append(field_name)
                            validation_notifications.append(warning)
                    for error in errors:
                        if error.get('type') == 'validation':
                            field_name = error.get('field')
                            if field_name:
                                found_fields.append(field_name)
                            validation_notifications.append(error)
        else:
            print(f"   ⚠️ Notifications field is unexpected type: {type(notifications)}")
            validation_notifications = []
        
        print(f"   Notifications: {len(validation_notifications)} validation notifications found")
        
        if not validation_notifications:
            if scenario.should_have_notifications:
                print(f"   ❌ Expected validation notifications but found none")
                print(f"   📋 Response keys: {list(response_data.keys())}")
                print(f"   📋 Full response: {response_data}")
                return {
                    "scenario": scenario.name,
                    "success": False,
                    "error": "No validation notifications found - validation system may be broken",
                    "expected": scenario.expected_validations,
                    "actual": []
                }
            else:
                print(f"   ✅ Correctly no notifications")
                return {"scenario": scenario.name, "success": True, "details": "No notifications as expected"}
        
        # Show found validation notifications
        print(f"   Found validation fields: {found_fields}")
        for notif in validation_notifications:
            field_name = notif.get('field') or notif.get('field_name')
            message = notif.get('message', 'No message')
            if field_name:
                print(f"     ✅ {field_name}: {message}")
            else:
                print(f"     ⚠️ Validation notification without field: {message}")
        
        # Check if we found expected validations
        missing_fields = [field for field in scenario.expected_validations if field not in found_fields]
        unexpected_fields = [field for field in found_fields if field not in scenario.expected_validations]
        
        success = len(missing_fields) == 0
        
        if missing_fields:
            print(f"   ❌ Missing expected validations: {missing_fields}")
        
        if unexpected_fields:
            print(f"   ⚠️ Unexpected validations: {unexpected_fields}")
        
        if success:
            print(f"   ✅ All expected validations found: {found_fields}")
        
        return {
            "scenario": scenario.name,
            "success": success,
            "expected": scenario.expected_validations,
            "found": found_fields,
            "missing": missing_fields,
            "unexpected": unexpected_fields,
            "total_notifications": len(notifications),
            "validation_notifications": len(validation_notifications)
        }
    
    async def run_comprehensive_validation_tests(self) -> List[Dict[str, Any]]:
        """Run all comprehensive validation tests"""
        
        print("🧪 COMPREHENSIVE VALIDATION TESTS (Live Server)")
        print("=" * 80)
        
        # Check server status
        if not self.check_server_status():
            print("❌ Cannot proceed - server not accessible")
            return []
        
        # Setup test data
        await self.setup_test_data()
        
        try:
            # Generate test scenarios
            scenarios = self.generate_validation_scenarios()
            print(f"Running {len(scenarios)} validation test scenarios...")
            
            results = []
            for i, scenario in enumerate(scenarios, 1):
                print(f"\n[{i}/{len(scenarios)}] Running scenario...")
                result = self.run_validation_test(scenario)
                results.append(result)
            
            return results
            
        finally:
            # Always cleanup test data
            await self.cleanup_test_data()
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print test summary"""
        print(f"\n{'='*80}")
        print("COMPREHENSIVE VALIDATION TEST RESULTS")
        print('='*80)
        
        total = len(results)
        passed = sum(1 for r in results if r.get('success', False))
        failed = total - passed
        
        print(f"Total scenarios: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        if total > 0:
            print(f"Success rate: {(passed/total)*100:.1f}%")
        print()
        
        # Show failed tests
        failed_results = [r for r in results if not r.get('success', False)]
        if failed_results:
            print("Failed Test Scenarios:")
            for result in failed_results:
                print(f"  ❌ {result['scenario']}: {result.get('error', 'Unknown error')}")
                if 'missing' in result and result['missing']:
                    print(f"     Missing validations: {result['missing']}")
        else:
            print("🎉 ALL VALIDATION TESTS PASSED!")
        
        if self.curl_output:
            print(f"\n📁 Curl commands saved to: tests/validation_curl.sh")
            print("   Run: chmod +x tests/validation_curl.sh && ./tests/validation_curl.sh")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Comprehensive Validation Tests (Live Server)')
    parser.add_argument('--server', default='http://localhost:5500',
                       help='Server URL (default: http://localhost:5500)')
    parser.add_argument('--curl', action='store_true',
                       help='Generate curl commands in validation_curl.sh')
    args = parser.parse_args()
    
    tester = LiveValidationTester(server_url=args.server, curl_output=args.curl)
    
    try:
        results = await tester.run_comprehensive_validation_tests()
        tester.print_summary(results)
        
        # Return exit code based on overall success
        all_successful = all(r.get('success', False) for r in results)
        return 0 if all_successful else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test runner failed: {e}")
        return 1

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))