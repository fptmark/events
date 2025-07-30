#!/usr/bin/env python3
"""
API validation test module - focused on basic API validation functionality
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.base_test import BaseTestFramework

class APITestModule(BaseTestFramework):
    def __init__(self, server_port: int = 5500, curl: bool = False):
        # Initialize BaseTestFramework with a dummy config (not used for API calls)
        super().__init__("dummy.json", f"http://localhost:{server_port}", curl=curl)
        self.server_port = server_port
        self.test_user_ids = {
            "bad_fk": "68814e0e73b517d9e048b093",
            "bad_enum": "68814e0e73b517d9e048b093", 
            "bad_currency": "68814e0e73b517d9e048b093",  # Use same ID as bad_enum since that one exists
            "bad_boolean": "68814e0e73b517d9e048b093",   # Use same ID as bad_enum since that one exists
            "bad_string": "68814e0e73b517d9e048b093"     # Use same ID as bad_enum since that one exists
        }
    
    def run_single_api_test(self, user_id: str, field_type: str) -> Dict[str, Any]:
        """Test a single API call with known bad data"""
        
        endpoint = f"/api/user/{user_id}"
        
        print(f"🧪 Testing GET {endpoint} for {field_type}")
        print("=" * 60)
        
        try:
            success, response_data = self.make_api_request("GET", endpoint, expected_status=200)
            
            if success:
                print(f"Status Code: 200")
                print()
                print("Response structure:")
                for key, value in response_data.items():
                    if key == 'data' and isinstance(value, dict):
                        print(f"  {key}: {{user object with {len(value)} fields}}")
                        # Show relevant field
                        if field_type == "bad_currency" and 'netWorth' in value:
                            print(f"    netWorth: {value['netWorth']}")
                        elif field_type == "bad_enum" and 'gender' in value:
                            print(f"    gender: {value['gender']}")
                        elif field_type == "bad_fk" and 'accountId' in value:
                            print(f"    accountId: {value['accountId']}")
                    elif key == 'notifications':
                        if value is None:
                            print(f"  {key}: null")
                        elif isinstance(value, list):
                            print(f"  {key}: [{len(value)} notifications]")
                            for i, notif in enumerate(value):
                                print(f"    {i+1}. {notif.get('type', 'UNKNOWN')}: {notif.get('message', 'no message')}")
                                if 'field_name' in notif:
                                    print(f"       Field: {notif['field_name']}")
                        else:
                            print(f"  {key}: {type(value).__name__}")
                    else:
                        print(f"  {key}: {type(value).__name__}")
                
                # Comprehensive validation analysis
                result = self._analyze_validation_completeness(response_data, field_type)
                
                return {
                    "test_type": "api",
                    "field_type": field_type,
                    "user_id": user_id,
                    "status_code": 200,
                    "response_data": response_data,
                    **result
                }
                
            else:
                print(f"❌ API request failed")
                return {
                    "test_type": "api",
                    "field_type": field_type,
                    "user_id": user_id,
                    "status_code": 0,
                    "success": False,
                    "details": "Request failed"
                }
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return {
                "test_type": "api",
                "field_type": field_type,
                "user_id": user_id,
                "status_code": 0,
                "success": False,
                "details": str(e)
            }
    
    def run_all_api_tests(self) -> List[Dict[str, Any]]:
        """Run all API validation tests"""
        results = []
        
        print("🧪 API VALIDATION TEST MODULE")
        print("=" * 80)
        
        # Test each field type
        for field_type, user_id in self.test_user_ids.items():
            result = self.run_single_api_test(user_id, field_type)
            results.append(result)
            print()
        
        return results
    
    def _analyze_validation_completeness(self, response_data: dict, field_type: str) -> dict:
        """Comprehensive analysis of validation response completeness"""
        
        # Define expected validation patterns for each field type
        expected_validations = {
            "bad_currency": {
                "field_name": "netWorth", 
                "expected_patterns": ["greater than or equal to 0", "negative", "invalid"],
                "description": "netWorth should be >= 0"
            },
            "bad_enum": {
                "field_name": "gender",
                "expected_patterns": ["must be male or female", "invalid enum", "not in allowed values"],
                "description": "gender must be male/female/other"
            },
            "bad_fk": {
                "field_name": "accountId",
                "expected_patterns": ["does not exist", "invalid reference", "not found"],
                "description": "accountId must reference existing account"
            },
            "bad_boolean": {
                "field_name": "isAccountOwner", 
                "expected_patterns": ["must be boolean", "true or false", "invalid boolean"],
                "description": "isAccountOwner must be boolean"
            },
            "bad_string": {
                "field_name": "username",
                "expected_patterns": ["at least 3 characters", "too short", "minimum length"],
                "description": "username must be at least 3 characters"
            }
        }
        
        expected = expected_validations.get(field_type)
        if not expected:
            return {"success": False, "details": f"Unknown field type: {field_type}"}
        
        # Check if notifications exist
        has_notifications = (
            'notifications' in response_data and 
            response_data['notifications'] is not None and
            len(response_data.get('notifications', [])) > 0
        )
        
        print()
        if not has_notifications:
            print("❌ No notifications found in response")
            return {
                "success": False, 
                "details": "No notifications in response - validation system not working",
                "expected_field": expected["field_name"],
                "expected_description": expected["description"]
            }
        
        print("✅ Found notifications in response")
        notifications = response_data['notifications']
        print(f"   Total notifications: {len(notifications)}")
        
        # Filter validation notifications
        validation_notifications = [n for n in notifications if n.get('type') == 'VALIDATION']
        
        if not validation_notifications:
            print("❌ No VALIDATION type notifications found")
            print("   Available notification types:", [n.get('type') for n in notifications])
            return {
                "success": False,
                "details": "No validation notifications found", 
                "expected_field": expected["field_name"],
                "expected_description": expected["description"]
            }
        
        print(f"✅ Found {len(validation_notifications)} validation notifications")
        
        # Look for the specific field error
        field_notifications = [n for n in validation_notifications 
                             if n.get('field_name') == expected["field_name"]]
        
        if not field_notifications:
            print(f"❌ No validation errors found for field '{expected['field_name']}'")
            print("   Fields with validation errors:", [n.get('field_name') for n in validation_notifications])
            return {
                "success": False,
                "details": f"No validation errors for {expected['field_name']}",
                "expected_field": expected["field_name"],
                "expected_description": expected["description"],
                "actual_fields": [n.get('field_name') for n in validation_notifications]
            }
        
        print(f"✅ Found {len(field_notifications)} validation errors for {expected['field_name']}")
        
        # Check if error message contains expected patterns
        found_expected_pattern = False
        for notification in field_notifications:
            message = notification.get('message', '').lower()
            print(f"   📝 Validation message: '{notification.get('message')}'")
            
            for pattern in expected["expected_patterns"]:
                if pattern.lower() in message:
                    print(f"   ✅ Found expected pattern: '{pattern}'")
                    found_expected_pattern = True
                    break
        
        if not found_expected_pattern:
            print(f"   ⚠️  Error message doesn't match expected patterns")
            print(f"   Expected patterns: {expected['expected_patterns']}")
            return {
                "success": False,
                "details": f"Validation error found but message doesn't match expected patterns",
                "expected_field": expected["field_name"],
                "expected_patterns": expected["expected_patterns"],
                "actual_messages": [n.get('message') for n in field_notifications]
            }
        
        # Success - found validation with expected pattern
        print(f"   🎉 COMPLETE: {expected['field_name']} validation working correctly")
        return {
            "success": True,
            "details": f"{expected['field_name']} validation complete with expected error pattern",
            "expected_field": expected["field_name"], 
            "found_messages": [n.get('message') for n in field_notifications]
        }


def main():
    """Main function for running API validation tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='API validation test module')
    parser.add_argument('--curl', action='store_true',
                       help='Log API calls to curl.sh file')
    parser.add_argument('--server-port', type=int, default=5500,
                       help='Server port (default: 5500)')
    
    args = parser.parse_args()
    
    # Initialize API test module with curl support
    api_tester = APITestModule(server_port=args.server_port, curl=args.curl)
    
    # Run all tests
    results = api_tester.run_all_api_tests()
    
    # Print summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get('success', False))
    failed_tests = total_tests - passed_tests
    
    print()
    print("=" * 80)
    print("API MODULE TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    return 0 if failed_tests == 0 else 1


if __name__ == "__main__":
    sys.exit(main())