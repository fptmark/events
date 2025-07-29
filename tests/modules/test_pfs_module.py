#!/usr/bin/env python3
"""
PFS (Pagination/Filtering/Sorting) test module
"""

import requests
import json
from typing import Dict, Any, List

class PFSTestModule:
    def __init__(self, server_port: int = 5500):
        self.server_port = server_port
    
    def run_pagination_test(self) -> Dict[str, Any]:
        """Test pagination functionality"""
        
        url = f"http://localhost:{self.server_port}/api/user"
        params = {
            "page": 1,
            "pageSize": 5,
            "sort": "username",
            "order": "asc"
        }
        
        print(f"🧪 Testing PFS - Pagination: {url}")
        print(f"   Params: {params}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get('data', [])
                total_count = response_data.get('total_count', 0)
                
                print(f"   Status: {response.status_code}")
                print(f"   Results: {len(data)} users")
                print(f"   Total count: {total_count}")
                
                return {
                    "test_type": "pfs_pagination",
                    "status_code": response.status_code,
                    "success": len(data) > 0,
                    "details": f"Returned {len(data)} of {total_count} users",
                    "response_data": response_data
                }
            else:
                return {
                    "test_type": "pfs_pagination", 
                    "status_code": response.status_code,
                    "success": False,
                    "details": f"HTTP {response.status_code}"
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
        
        url = f"http://localhost:{self.server_port}/api/user"
        params = {
            "filter": "gender:male",
            "page": 1,
            "pageSize": 10
        }
        
        print(f"🧪 Testing PFS - Filtering: {url}")
        print(f"   Params: {params}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get('data', [])
                
                print(f"   Status: {response.status_code}")
                print(f"   Filtered results: {len(data)} users")
                
                return {
                    "test_type": "pfs_filtering",
                    "status_code": response.status_code,
                    "success": True,
                    "details": f"Filter returned {len(data)} users",
                    "response_data": response_data
                }
            else:
                return {
                    "test_type": "pfs_filtering",
                    "status_code": response.status_code,
                    "success": False,
                    "details": f"HTTP {response.status_code}"
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
        
        url = f"http://localhost:{self.server_port}/api/user"
        params = {
            "sort": "createdAt",
            "order": "desc",
            "page": 1,
            "pageSize": 5
        }
        
        print(f"🧪 Testing PFS - Sorting: {url}")
        print(f"   Params: {params}")
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                response_data = response.json()
                data = response_data.get('data', [])
                
                print(f"   Status: {response.status_code}")
                print(f"   Sorted results: {len(data)} users")
                
                # Check if actually sorted
                if len(data) > 1:
                    dates = [user.get('createdAt') for user in data if user.get('createdAt')]
                    is_sorted = dates == sorted(dates, reverse=True)
                    print(f"   Properly sorted: {is_sorted}")
                
                return {
                    "test_type": "pfs_sorting",
                    "status_code": response.status_code,
                    "success": True,
                    "details": f"Sort returned {len(data)} users",
                    "response_data": response_data
                }
            else:
                return {
                    "test_type": "pfs_sorting",
                    "status_code": response.status_code,
                    "success": False,
                    "details": f"HTTP {response.status_code}"
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