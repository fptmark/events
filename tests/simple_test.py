#!/usr/bin/env python3
"""
Simple, direct API tests without complex framework overhead.
Just hits the endpoints and reports results.
"""

import requests
import time
import sys

BASE_URL = "http://localhost:5500"

def test_endpoint(url, description):
    """Test a single endpoint"""
    full_url = f"{BASE_URL}{url}"
    print(f"Testing: {description}")
    print(f"  URL: {url}")
    
    try:
        start = time.time()
        response = requests.get(full_url, timeout=10)
        duration = (time.time() - start) * 1000
        
        print(f"  Status: {response.status_code} ({duration:.0f}ms)")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'data' in data and isinstance(data['data'], list):
                    print(f"  Data: {len(data['data'])} items")
                print(f"  ✅ PASS")
                return True
            except:
                print(f"  ✅ PASS (non-JSON response)")
                return True
        else:
            print(f"  ❌ FAIL - Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ FAIL - {e}")
        return False

def main():
    """Run simple API tests"""
    print("🧪 SIMPLE API TESTS")
    print("=" * 50)
    
    tests = [
        # Basic pagination
        ("/api/user", "Basic user list"),
        ("/api/user?pageSize=5", "Pagination with page size"),
        
        # Single field sorting  
        ("/api/user?sort=username", "Sort by username asc"),
        ("/api/user?sort=-username", "Sort by username desc"),
        ("/api/user?sort=createdAt", "Sort by createdAt asc"),
        ("/api/user?sort=-createdAt", "Sort by createdAt desc"),
        
        # Multi-field sorting (the problematic ones)
        ("/api/user?sort=firstName,lastName", "Multi-field sort: firstName,lastName"),
        ("/api/user?sort=firstName,-createdAt", "Multi-field sort: firstName,-createdAt"),
        ("/api/user?sort=-lastName,firstName", "Multi-field sort: -lastName,firstName"),
        
        # Sorting with pagination
        ("/api/user?sort=username&pageSize=3", "Sort with pagination"),
        
        # Basic filtering
        ("/api/user?filter=gender:male", "Filter by gender"),
        ("/api/user?filter=isAccountOwner:true", "Filter by isAccountOwner"),
        
        # Combined operations
        ("/api/user?filter=gender:male&sort=username", "Filter + sort"),
        ("/api/user?filter=gender:male&sort=username&pageSize=5", "Filter + sort + pagination"),
    ]
    
    passed = 0
    total = len(tests)
    
    for i, (url, description) in enumerate(tests, 1):
        print(f"\n[{i}/{total}] ", end="")
        if test_endpoint(url, description):
            passed += 1
        time.sleep(0.1)  # Small delay between requests
    
    print(f"\n{'=' * 50}")
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"💥 {total - passed} TESTS FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())