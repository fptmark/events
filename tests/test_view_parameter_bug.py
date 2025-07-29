#!/usr/bin/env python3
"""
Critical Bug Test: View Parameter Dependency

This test specifically validates the critical bug discovered by the user:
- Notification system returns null when view parameter is missing
- Notification system works correctly when view parameter is present

This test framework is designed to CATCH this specific pattern.
"""

import sys
import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import urllib.parse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_data_setup import TestDataCreator

@dataclass
class ViewParameterTestCase:
    """Test case specifically for view parameter dependency bug"""
    name: str
    description: str
    url_without_view: str
    url_with_view: str
    expected_validations: List[str]  # Field names that should have validation errors

class ViewParameterBugTester:
    def __init__(self, server_url: str = "http://localhost:5500"):
        self.server_url = server_url
        self.test_data = {}
        self.data_creator = None
    
    async def setup_test_data(self):
        """Create test data for validation testing"""
        print("🧪 Setting up test data for view parameter bug tests...")
        
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
    
    def generate_view_parameter_test_cases(self) -> List[ViewParameterTestCase]:
        """Generate test cases specifically for view parameter dependency bug"""
        
        if not self.test_data:
            raise ValueError("Test data not initialized. Call setup_test_data() first.")
        
        # Use test users with specific validation issues  
        bad_enum_user = self.test_data["bad_enum"]
        bad_currency_user = self.test_data["bad_currency"]
        bad_fk_user = self.test_data["bad_fk"]
        multiple_errors_user = self.test_data["multiple_errors"]
        
        # View parameter for FK processing
        view_param = urllib.parse.quote('{"account":["id"]}')
        
        test_cases = [
            # Test Case 1: Enum validation - compare with and without view
            ViewParameterTestCase(
                name="enum_validation_comparison",
                description="CRITICAL TEST: Compare enum validation with and without view parameter",
                url_without_view=f"/api/user/{bad_enum_user}",
                url_with_view=f"/api/user/{bad_enum_user}?view={view_param}",
                expected_validations=["gender"]
            ),
            
            # Test Case 2: Currency validation - compare with and without view
            ViewParameterTestCase(
                name="currency_validation_comparison",
                description="CRITICAL TEST: Compare currency validation with and without view parameter",
                url_without_view=f"/api/user/{bad_currency_user}",
                url_with_view=f"/api/user/{bad_currency_user}?view={view_param}",
                expected_validations=["netWorth"]
            ),
            
            # Test Case 3: FK validation - compare with and without view
            ViewParameterTestCase(
                name="fk_validation_comparison",
                description="CRITICAL TEST: Compare FK validation with and without view parameter",
                url_without_view=f"/api/user/{bad_fk_user}",
                url_with_view=f"/api/user/{bad_fk_user}?view={view_param}",
                expected_validations=["accountId"]
            ),
            
            # Test Case 4: Multiple errors - compare with and without view
            ViewParameterTestCase(
                name="multiple_errors_comparison",
                description="CRITICAL TEST: Compare multiple validation errors with and without view parameter",
                url_without_view=f"/api/user/{multiple_errors_user}",
                url_with_view=f"/api/user/{multiple_errors_user}?view={view_param}",
                expected_validations=["gender", "netWorth", "accountId"]
            ),
            
            # Test Case 5: List endpoint - compare with and without view
            ViewParameterTestCase(
                name="list_endpoint_comparison",
                description="CRITICAL TEST: Compare list endpoint validation with and without view parameter",
                url_without_view=f"/api/user?filter=id:{bad_enum_user}&pageSize=5",
                url_with_view=f"/api/user?view={view_param}&filter=id:{bad_enum_user}&pageSize=5",
                expected_validations=["gender"]
            )
        ]
        
        return test_cases
    
    def test_single_url(self, url: str, description: str, expected_validations: List[str]) -> Dict[str, Any]:
        """Test a single URL and analyze the response"""
        full_url = f"{self.server_url}{url}"
        
        try:
            start_time = time.time()
            response = requests.get(full_url, timeout=10)
            duration = time.time() - start_time
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "response_text": response.text,
                    "duration": duration
                }
            
            response_data = response.json()
            notifications = response_data.get('notifications')
            
            # Critical bug detection
            if notifications is None:
                return {
                    "success": False,
                    "error": "CRITICAL BUG: Notifications field is null",
                    "notifications": None,
                    "expected_validations": expected_validations,
                    "found_validations": [],
                    "duration": duration,
                    "critical_bug_detected": True
                }
            
            # Handle both list format and entity-grouped dict format
            validation_notifications = []
            found_validations = []
            
            if isinstance(notifications, list):
                # Standard list format
                validation_notifications = [n for n in notifications if n.get('type') in ['VALIDATION', 'validation']]
                found_validations = [n.get('field_name') or n.get('field') for n in validation_notifications if n.get('field_name') or n.get('field')]
            elif isinstance(notifications, dict):
                # Entity-grouped dict format
                for entity_id, entity_data in notifications.items():
                    if isinstance(entity_data, dict):
                        warnings = entity_data.get('warnings', [])
                        errors = entity_data.get('errors', [])
                        for warning in warnings:
                            if warning.get('type') == 'validation':
                                field_name = warning.get('field')
                                if field_name:
                                    found_validations.append(field_name)
                                validation_notifications.append(warning)
                        for error in errors:
                            if error.get('type') == 'validation':
                                field_name = error.get('field')
                                if field_name:
                                    found_validations.append(field_name)
                                validation_notifications.append(error)
            else:
                return {
                    "success": False,
                    "error": f"Notifications field is unexpected type: {type(notifications)}",
                    "notifications": notifications,
                    "expected_validations": expected_validations,
                    "found_validations": [],
                    "duration": duration,
                    "critical_bug_detected": False
                }
            
            # Check if all expected validations are found
            missing_validations = [v for v in expected_validations if v not in found_validations]
            success = len(missing_validations) == 0
            
            return {
                "success": success,
                "error": f"Missing validations: {missing_validations}" if not success else None,
                "notifications": notifications,
                "expected_validations": expected_validations,
                "found_validations": found_validations,
                "missing_validations": missing_validations,
                "total_notifications": len(notifications),
                "validation_notifications": len(validation_notifications),
                "duration": duration,
                "critical_bug_detected": False
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "notifications": None,
                "expected_validations": expected_validations,
                "found_validations": [],
                "duration": 0,
                "critical_bug_detected": False
            }
    
    def run_view_parameter_test_case(self, test_case: ViewParameterTestCase) -> Dict[str, Any]:
        """Run a single view parameter test case (tests both URLs)"""
        
        print(f"\n🧪 CRITICAL BUG TEST: {test_case.name}")
        print(f"   Description: {test_case.description}")
        print(f"   Expected validations: {test_case.expected_validations}")
        
        # Test URL without view parameter
        print(f"\n   📋 Testing WITHOUT view parameter:")
        print(f"   URL: {test_case.url_without_view}")
        without_view_result = self.test_single_url(
            test_case.url_without_view, 
            "WITHOUT view parameter", 
            test_case.expected_validations
        )
        
        # Test URL with view parameter
        print(f"\n   📋 Testing WITH view parameter:")
        print(f"   URL: {test_case.url_with_view}")
        with_view_result = self.test_single_url(
            test_case.url_with_view, 
            "WITH view parameter", 
            test_case.expected_validations
        )
        
        # Analyze the results for the critical bug pattern
        return self._analyze_view_parameter_results(test_case, without_view_result, with_view_result)
    
    def _analyze_view_parameter_results(self, test_case: ViewParameterTestCase, 
                                       without_view: Dict[str, Any], 
                                       with_view: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze results to detect the view parameter dependency bug"""
        
        without_view_success = without_view["success"]
        with_view_success = with_view["success"]
        
        without_view_null = without_view.get("critical_bug_detected", False)
        with_view_null = with_view.get("critical_bug_detected", False)
        
        print(f"\n   📊 ANALYSIS:")
        print(f"   WITHOUT view parameter: {'✅ SUCCESS' if without_view_success else '❌ FAILED'} " +
              f"({without_view['duration']:.1f}s)")
        if without_view_null:
            print(f"      🚨 CRITICAL BUG: Notifications are NULL")
        elif not without_view_success:
            print(f"      Error: {without_view.get('error', 'Unknown')}")
        else:
            print(f"      Found validations: {without_view['found_validations']}")
        
        print(f"   WITH view parameter: {'✅ SUCCESS' if with_view_success else '❌ FAILED'} " +
              f"({with_view['duration']:.1f}s)")
        if with_view_null:
            print(f"      🚨 CRITICAL BUG: Notifications are NULL (unexpected!)")
        elif not with_view_success:
            print(f"      Error: {with_view.get('error', 'Unknown')}")
        else:
            print(f"      Found validations: {with_view['found_validations']}")
        
        # Determine bug pattern
        bug_pattern = "unknown"
        if without_view_null and not with_view_null and with_view_success:
            bug_pattern = "view_parameter_dependency"
            print(f"   🚨 BUG CONFIRMED: Notifications only work WITH view parameter!")
        elif without_view_success and with_view_success:
            bug_pattern = "no_bug_detected"
            print(f"   ✅ GOOD: Notifications work in both scenarios")
        elif without_view_null and with_view_null:
            bug_pattern = "notifications_completely_broken"
            print(f"   💥 WORSE: Notifications are broken in BOTH scenarios!")
        elif not without_view_success and not with_view_success:
            bug_pattern = "validation_issues"
            print(f"   ⚠️ Both scenarios have validation issues (not null notifications)")
        else:
            bug_pattern = "mixed_results"
            print(f"   🤔 Mixed results - needs investigation")
        
        return {
            "test_case": test_case.name,
            "bug_pattern": bug_pattern,
            "without_view_result": without_view,
            "with_view_result": with_view,
            "critical_bug_confirmed": bug_pattern == "view_parameter_dependency",
            "both_scenarios_work": bug_pattern == "no_bug_detected",
            "both_scenarios_broken": bug_pattern == "notifications_completely_broken"
        }
    
    async def run_all_view_parameter_tests(self) -> List[Dict[str, Any]]:
        """Run all view parameter dependency tests"""
        
        print("🚨 CRITICAL BUG TEST SUITE: VIEW PARAMETER DEPENDENCY")
        print("=" * 80)
        print("Testing the user-discovered bug:")
        print("- Notifications return null when view parameter is missing")  
        print("- Notifications work correctly when view parameter is present")
        print("=" * 80)
        
        # Check server status
        if not self.check_server_status():
            print("❌ Cannot proceed - server not accessible")
            return []
        
        # Setup test data
        await self.setup_test_data()
        
        try:
            # Generate test cases
            test_cases = self.generate_view_parameter_test_cases()
            print(f"Running {len(test_cases)} critical bug test cases...")
            
            results = []
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n[{i}/{len(test_cases)}] Running test case...")
                result = self.run_view_parameter_test_case(test_case)
                results.append(result)
            
            return results
            
        finally:
            # Always cleanup test data
            await self.cleanup_test_data()
    
    def print_final_analysis(self, results: List[Dict[str, Any]]):
        """Print comprehensive analysis of the view parameter dependency bug"""
        print(f"\n{'='*80}")
        print("CRITICAL BUG TEST RESULTS - VIEW PARAMETER DEPENDENCY ANALYSIS")
        print('='*80)
        
        total_tests = len(results)
        bug_confirmed_count = sum(1 for r in results if r["critical_bug_confirmed"])
        both_work_count = sum(1 for r in results if r["both_scenarios_work"])
        both_broken_count = sum(1 for r in results if r["both_scenarios_broken"])
        
        print(f"Total test cases: {total_tests}")
        print(f"Bug confirmed (view dependency): {bug_confirmed_count}")
        print(f"Both scenarios work: {both_work_count}")
        print(f"Both scenarios broken: {both_broken_count}")
        print()
        
        # Overall assessment
        if bug_confirmed_count > 0:
            print("🚨 CRITICAL BUG CONFIRMED!")
            print("   The notification system has a view parameter dependency bug.")
            print("   Notifications only work when a view parameter is present.")
            print("   This is a critical issue that breaks validation feedback.")
        elif both_work_count == total_tests:
            print("✅ BUG APPEARS TO BE FIXED!")
            print("   All test cases show notifications working in both scenarios.")
            print("   The view parameter dependency bug may have been resolved.")
        elif both_broken_count > 0:
            print("💥 NOTIFICATIONS SYSTEM IS COMPLETELY BROKEN!")
            print("   Notifications don't work in ANY scenario.")
            print("   This is worse than the original bug.")
        else:
            print("🤔 MIXED RESULTS - NEEDS INVESTIGATION")
            print("   Test results show inconsistent patterns.")
        
        print()
        print("Detailed Results by Test Case:")
        for result in results:
            test_name = result["test_case"]
            pattern = result["bug_pattern"]
            
            if pattern == "view_parameter_dependency":
                status = "🚨 BUG CONFIRMED"
            elif pattern == "no_bug_detected":
                status = "✅ WORKING"
            elif pattern == "notifications_completely_broken":
                status = "💥 COMPLETELY BROKEN"
            else:
                status = f"⚠️ {pattern.replace('_', ' ').upper()}"
            
            print(f"  {status}: {test_name}")
            
            # Show details for bug cases
            if pattern == "view_parameter_dependency":
                without_error = result["without_view_result"].get("error", "Unknown")
                print(f"    Without view: {without_error}")
                print(f"    With view: SUCCESS")
        
        print()
        if bug_confirmed_count > 0:
            print("🔧 RECOMMENDED ACTIONS:")
            print("1. Fix the notification system to work without view parameters")
            print("2. Investigate why view parameters affect notification context")
            print("3. Add proper test coverage for this scenario")
            print("4. Ensure all validation errors are properly reported")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Critical Bug Test: View Parameter Dependency')
    parser.add_argument('--server', default='http://localhost:5500',
                       help='Server URL (default: http://localhost:5500)')
    args = parser.parse_args()
    
    tester = ViewParameterBugTester(server_url=args.server)
    
    try:
        results = await tester.run_all_view_parameter_tests()
        tester.print_final_analysis(results)
        
        # Return exit code based on bug detection
        bug_confirmed = any(r["critical_bug_confirmed"] for r in results)
        return 1 if bug_confirmed else 0  # Exit 1 if bug confirmed (failure)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n❌ Test runner failed: {e}")
        return 1

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))