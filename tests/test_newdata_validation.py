#!/usr/bin/env python3
"""
New Data Validation Test Module

Standalone test that can wipe database, create controlled test data,
and run comprehensive validation tests. Designed to be called by CT.
"""

import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_data_setup import TestDataCreator
from tests.test_validation_live import LiveValidationTester
from tests.test_view_parameter_bug import ViewParameterBugTester

class NewDataValidationTester:
    def __init__(self, config_file: str = "mongo.json", server_url: str = "http://localhost:5500", curl_output: bool = False):
        self.config_file = config_file
        self.server_url = server_url
        self.curl_output = curl_output
        self.data_creator = TestDataCreator()
        self.validation_tester = LiveValidationTester(server_url=server_url, curl_output=curl_output)
        self.bug_tester = ViewParameterBugTester(server_url=server_url)
    
    async def run_newdata_validation_tests(self) -> List[Dict[str, Any]]:
        """Complete newdata validation test cycle"""
        
        print("🧪 NEW DATA VALIDATION TEST MODULE")
        print("=" * 80)
        print("This will wipe test data, create controlled data, and run validation tests")
        print()
        
        try:
            # Step 1: Setup database connection
            await self.data_creator.setup_database(self.config_file)
            
            # Step 2: Wipe existing test data
            print("🧹 Step 1: Wiping existing test data...")
            await self.data_creator.wipe_all_test_data()
            
            # Step 3: Create controlled test data with known validation issues
            print("\n📊 Step 2: Creating controlled test data...")
            test_data = await self.data_creator.create_comprehensive_test_data()
            
            # Step 4: Check server connectivity first
            if not self.validation_tester.check_server_status():
                print("❌ Cannot proceed - server not accessible")
                return []
            
            # Step 5: Update validation tester with the new test data
            print("\n✅ Step 3: Running comprehensive validation tests...")
            self.validation_tester.test_data = test_data
            
            # Step 6: FIRST - Run critical bug detection tests
            print("\n🚨 Step 3a: Running CRITICAL BUG DETECTION tests...")
            self.bug_tester.test_data = test_data
            bug_test_cases = self.bug_tester.generate_view_parameter_test_cases()
            
            print(f"Running {len(bug_test_cases)} critical bug test cases...")
            bug_results = []
            for i, test_case in enumerate(bug_test_cases, 1):
                print(f"\n[BUG-{i}/{len(bug_test_cases)}] Critical bug test...")
                result = self.bug_tester.run_view_parameter_test_case(test_case)
                bug_results.append(result)
            
            # Step 7: Run standard validation tests
            print(f"\n✅ Step 3b: Running standard validation tests...")
            scenarios = self.validation_tester.generate_validation_scenarios()
            
            print(f"Running {len(scenarios)} validation test scenarios...")
            validation_results = []
            for i, scenario in enumerate(scenarios, 1):
                print(f"\n[STD-{i}/{len(scenarios)}] {scenario.name}")
                print(f"   Description: {scenario.description}")
                result = self.validation_tester.run_validation_test(scenario)
                validation_results.append(result)
                
                # Show immediate result
                if result.get('success', False):
                    validations = result.get('found', [])
                    print(f"   ✅ PASS - Found validations: {validations}")
                else:
                    error = result.get('error', 'Unknown error')
                    print(f"   ❌ FAIL - {error}")
            
            # Combine results with bug test results marked for priority
            combined_results = []
            for bug_result in bug_results:
                combined_results.append({
                    "test_type": "critical_bug_detection",
                    "bug_result": bug_result,
                    "success": not bug_result["critical_bug_confirmed"]  # Success = no bug confirmed
                })
            
            for validation_result in validation_results:
                combined_results.append({
                    "test_type": "standard_validation", 
                    "validation_result": validation_result,
                    "success": validation_result.get('success', False)
                })
            
            return combined_results
            
        finally:
            # Always cleanup database connection
            await self.data_creator.cleanup_database()
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print enhanced test summary with critical bug analysis"""
        
        print(f"\n{'='*80}")
        print("ENHANCED VALIDATION TEST RESULTS - CRITICAL BUG DETECTION")
        print('='*80)
        
        # Separate results by type
        bug_results = [r["bug_result"] for r in results if r.get("test_type") == "critical_bug_detection"]
        validation_results = [r["validation_result"] for r in results if r.get("test_type") == "standard_validation"]
        
        # Print critical bug analysis first
        if bug_results:
            print("🚨 CRITICAL BUG TEST RESULTS:")
            bug_confirmed_count = sum(1 for r in bug_results if r["critical_bug_confirmed"])
            both_work_count = sum(1 for r in bug_results if r["both_scenarios_work"])
            
            print(f"   Total critical bug tests: {len(bug_results)}")
            print(f"   View parameter dependency confirmed: {bug_confirmed_count}")
            print(f"   Both scenarios working: {both_work_count}")
            
            # DEBUG: Show individual bug test results
            for i, result in enumerate(bug_results):
                test_name = result["test_case"]
                pattern = result["bug_pattern"]
                print(f"   DEBUG: Bug test {i+1} ({test_name}): {pattern}")
            
            if bug_confirmed_count > 0:
                print(f"   🚨 CRITICAL BUG CONFIRMED: Notifications only work with view parameter!")
            elif both_work_count == len(bug_results):
                print(f"   ✅ NO BUG DETECTED: Notifications work in both scenarios")
            else:
                print(f"   🤔 MIXED RESULTS: Needs investigation")
            print()
        else:
            print("🚨 CRITICAL BUG TEST RESULTS:")
            print("   ❌ NO BUG TESTS RAN - This indicates a setup failure!")
            print()
        
        # Print standard validation results
        if validation_results:
            print("📊 STANDARD VALIDATION TEST RESULTS:")
            total = len(validation_results)
            passed = sum(1 for r in validation_results if r.get('success', False))
            failed = total - passed
            
            print(f"   Total scenarios: {total}")
            print(f"   Passed: {passed}")
            print(f"   Failed: {failed}")
            if total > 0:
                print(f"   Success rate: {(passed/total)*100:.1f}%")
            print()
            
            # Show failed standard tests
            failed_results = [r for r in validation_results if not r.get('success', False)]
            if failed_results:
                print("   Failed Standard Test Scenarios:")
                for result in failed_results:
                    print(f"     ❌ {result['scenario']}: {result.get('error', 'Unknown error')}")
                    if 'missing' in result and result['missing']:
                        print(f"        Missing validations: {result['missing']}")
        
        # Overall assessment
        print("🔍 OVERALL ASSESSMENT:")
        critical_bug_present = any(r["critical_bug_confirmed"] for r in bug_results)
        null_notifications_detected = any("null" in str(r).lower() or "critical bug" in str(r) for r in bug_results)
        
        if critical_bug_present or null_notifications_detected:
            print("   🚨 CRITICAL ISSUE: View parameter dependency bug detected!")
            print("   🔧 PRIORITY: Fix the notification system before proceeding")
            print("   📋 The notification system only works when view parameters are present")
        else:
            print("   ✅ No critical bugs detected in notification system")
            if validation_results:
                all_validation_passed = all(r.get('success', False) for r in validation_results)
                if all_validation_passed:
                    print("   🎉 All validation tests passed!")
                else:
                    print("   ⚠️ Some validation tests failed - review individual cases")
        
        if self.curl_output:
            print(f"\n📁 Curl commands saved to: tests/validation_curl.sh")
            print("   Run: chmod +x tests/validation_curl.sh && ./tests/validation_curl.sh")

async def main():
    """Standalone execution"""
    import argparse
    parser = argparse.ArgumentParser(description='New Data Validation Test Module')
    parser.add_argument('--config', default='mongo.json',
                       help='Config file (default: mongo.json)')
    parser.add_argument('--server', default='http://localhost:5500',
                       help='Server URL (default: http://localhost:5500)')
    parser.add_argument('--curl', action='store_true',
                       help='Generate curl commands in validation_curl.sh')
    args = parser.parse_args()
    
    tester = NewDataValidationTester(
        config_file=args.config,
        server_url=args.server,
        curl_output=args.curl
    )
    
    try:
        results = await tester.run_newdata_validation_tests()
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
    sys.exit(asyncio.run(main()))