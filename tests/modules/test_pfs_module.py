#!/usr/bin/env python3
"""
PFS (Pagination/Filtering/Sorting) test module
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.base_test import BaseTestFramework

class PFSTestModule(BaseTestFramework):
    def __init__(self, server_port: int = 5500, curl: bool = False):
        # Initialize BaseTestFramework with a dummy config (not used for API calls)
        super().__init__("dummy.json", f"http://localhost:{server_port}", curl=curl)
        self.server_port = server_port
    
    def run_pagination_test(self) -> Dict[str, Any]:
        """Test pagination functionality"""
        
        # Build endpoint with query parameters
        endpoint = "/api/user?page=1&pageSize=5&sort=username&order=asc"
        
        print(f"🧪 Testing PFS - Pagination: {endpoint}")
        
        try:
            success, response_data = self.make_api_request("GET", endpoint, expected_status=200)
            
            if success:
                data = response_data.get('data', [])
                total_count = response_data.get('total_count', 0)
                
                print(f"   Status: 200")
                print(f"   Results: {len(data)} users")
                print(f"   Total count: {total_count}")
                
                return {
                    "test_type": "pfs_pagination",
                    "status_code": 200,
                    "success": len(data) > 0,
                    "details": f"Returned {len(data)} of {total_count} users",
                    "response_data": response_data
                }
            else:
                return {
                    "test_type": "pfs_pagination", 
                    "status_code": 0,
                    "success": False,
                    "details": "Request failed"
                }
        except Exception as e:
            return {
                "test_type": "pfs_pagination",
                "status_code": 0,
                "success": False,
                "details": str(e)
            }
    
    def run_filtering_test(self) -> Dict[str, Any]:
        """Test filtering functionality"""
        
        # Build endpoint with query parameters
        endpoint = "/api/user?filter=gender:male&page=1&pageSize=10"
        
        print(f"🧪 Testing PFS - Filtering: {endpoint}")
        
        try:
            success, response_data = self.make_api_request("GET", endpoint, expected_status=200)
            
            if success:
                data = response_data.get('data', [])
                
                print(f"   Status: 200")
                print(f"   Filtered results: {len(data)} users")
                
                return {
                    "test_type": "pfs_filtering",
                    "status_code": 200,
                    "success": True,
                    "details": f"Filter returned {len(data)} users",
                    "response_data": response_data
                }
            else:
                return {
                    "test_type": "pfs_filtering",
                    "status_code": 0,
                    "success": False,
                    "details": "Request failed"
                }
        except Exception as e:
            return {
                "test_type": "pfs_filtering",
                "status_code": 0,
                "success": False,
                "details": str(e)
            }
    
    def run_sorting_test(self) -> Dict[str, Any]:
        """Test sorting functionality"""
        
        # Build endpoint with query parameters
        endpoint = "/api/user?sort=createdAt&order=desc&page=1&pageSize=5"
        
        print(f"🧪 Testing PFS - Sorting: {endpoint}")
        
        try:
            success, response_data = self.make_api_request("GET", endpoint, expected_status=200)
            
            if success:
                data = response_data.get('data', [])
                
                print(f"   Status: 200")
                print(f"   Sorted results: {len(data)} users")
                
                # Check if actually sorted
                if len(data) > 1:
                    dates = [user.get('createdAt') for user in data if user.get('createdAt')]
                    is_sorted = dates == sorted(dates, reverse=True)
                    print(f"   Properly sorted: {is_sorted}")
                
                return {
                    "test_type": "pfs_sorting",
                    "status_code": 200,
                    "success": True,
                    "details": f"Sort returned {len(data)} users",
                    "response_data": response_data
                }
            else:
                return {
                    "test_type": "pfs_sorting",
                    "status_code": 0,
                    "success": False,
                    "details": "Request failed"
                }
        except Exception as e:
            return {
                "test_type": "pfs_sorting",
                "status_code": 0,
                "success": False,
                "details": str(e)
            }
    
    def run_all_pfs_tests(self) -> List[Dict[str, Any]]:
        """Run all PFS tests"""
        results = []
        
        print("🧪 PFS TEST MODULE")
        print("=" * 80)
        
        # Run each PFS test
        results.append(self.run_pagination_test())
        print()
        results.append(self.run_filtering_test())
        print()
        results.append(self.run_sorting_test())
        print()
        
        return results


def main():
    """Main function for running PFS tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PFS test module')
    parser.add_argument('--curl', action='store_true',
                       help='Log API calls to curl.sh file')
    parser.add_argument('--server-port', type=int, default=5500,
                       help='Server port (default: 5500)')
    
    args = parser.parse_args()
    
    # Initialize PFS test module with curl support
    pfs_tester = PFSTestModule(server_port=args.server_port, curl=args.curl)
    
    # Run all tests
    results = pfs_tester.run_all_pfs_tests()
    
    # Print summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get('success', False))
    failed_tests = total_tests - passed_tests
    
    print()
    print("=" * 80)
    print("PFS MODULE TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    return 0 if failed_tests == 0 else 1


if __name__ == "__main__":
    sys.exit(main())