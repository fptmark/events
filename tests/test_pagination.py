#!/usr/bin/env python3
"""
Pagination tests for User endpoints.

Tests pagination functionality:
- GET /user?page=X&pageSize=Y
- Page boundary conditions
- Invalid pagination parameters
- Pagination metadata validation

Supports both standalone execution and orchestrated testing.
Can run across all 4 modes: MongoDB/Elasticsearch with/without validation.

Usage:
    # Standalone with specific config
    python test_pagination.py --config mongo.json
    
    # Standalone across all 4 modes
    python test_pagination.py --all-modes
    
    # With verbose output and curl generation
    python test_pagination.py --config es.json --verbose --curl
"""

import sys
import argparse
import math
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_common import (
    TestRunner, APIClient, ResponseValidator, TestMode,
    ConfigManager, DatabaseTestHelper, TestDataManager
)

class PaginationTestSuite:
    """Pagination test suite"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.runner = TestRunner("Pagination Tests", verbose=verbose)
    
    def test_basic_pagination(self, config_file: str, curl: bool = False) -> bool:
        """Test basic pagination functionality"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test first page with small page size
            page = 1
            page_size = 3
            
            print(f"  🔍 Testing pagination: page={page}, pageSize={page_size}")
            
            response = client.get('/api/user', params={'page': page, 'pageSize': page_size})
            
            # Should return 200 with pagination structure
            is_valid, msg = ResponseValidator.validate_pagination_response(response)
            if not is_valid:
                print(f"  ❌ Pagination response validation failed: {msg}")
                return False
            
            data = response.json_data
            users = data['data']
            pagination = data['pagination']
            
            # Verify pagination metadata
            expected_fields = ['page', 'pageSize', 'totalCount', 'totalPages']
            for field in expected_fields:
                if field not in pagination:
                    print(f"  ❌ Missing pagination field: {field}")
                    return False
            
            # Verify values
            if pagination['page'] != page:
                print(f"  ❌ Wrong page number: expected {page}, got {pagination['page']}")
                return False
            
            if pagination['pageSize'] != page_size:
                print(f"  ❌ Wrong page size: expected {page_size}, got {pagination['pageSize']}")
                return False
            
            # Verify data count doesn't exceed page size
            if len(users) > page_size:
                print(f"  ❌ Too many results: expected max {page_size}, got {len(users)}")
                return False
            
            # Calculate expected total pages
            total_count = pagination['totalCount']
            expected_total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
            
            if pagination['totalPages'] != expected_total_pages:
                print(f"  ❌ Wrong total pages: expected {expected_total_pages}, got {pagination['totalPages']}")
                return False
            
            print(f"  ✅ Basic pagination working correctly")
            print(f"     Page {page} of {pagination['totalPages']}, {len(users)} users, {total_count} total")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_basic_pagination: {e}")
            return False
    
    def test_pagination_page_boundaries(self, config_file: str, curl: bool = False) -> bool:
        """Test pagination at page boundaries"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # First get total count
            response = client.get('/api/user', params={'page': 1, 'pageSize': 1})
            if response.status_code != 200 or not response.json_data:
                print("  ❌ Could not get total count")
                return False
            
            total_count = response.json_data['pagination']['totalCount']
            if total_count == 0:
                print("  ⚠️  No users found - skipping boundary tests")
                return True
            
            page_size = 2
            total_pages = math.ceil(total_count / page_size)
            
            print(f"  🔍 Testing boundaries: {total_count} users, page size {page_size}, {total_pages} pages")
            
            # Test first page
            response = client.get('/api/user', params={'page': 1, 'pageSize': page_size})
            if response.status_code != 200:
                print(f"  ❌ First page failed: {response.status_code}")
                return False
            
            first_page_data = response.json_data
            first_page_users = first_page_data['data']
            print(f"     First page: {len(first_page_users)} users")
            
            # Test last page
            if total_pages > 1:
                response = client.get('/api/user', params={'page': total_pages, 'pageSize': page_size})
                if response.status_code != 200:
                    print(f"  ❌ Last page failed: {response.status_code}")
                    return False
                
                last_page_data = response.json_data
                last_page_users = last_page_data['data']
                print(f"     Last page: {len(last_page_users)} users")
                
                # Last page might have fewer users
                expected_last_page_count = total_count % page_size
                if expected_last_page_count == 0:
                    expected_last_page_count = page_size
                
                if len(last_page_users) != expected_last_page_count:
                    print(f"  ❌ Last page count wrong: expected {expected_last_page_count}, got {len(last_page_users)}")
                    return False
            
            print(f"  ✅ Page boundaries working correctly")
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_pagination_page_boundaries: {e}")
            return False
    
    def test_pagination_beyond_bounds(self, config_file: str, curl: bool = False) -> bool:
        """Test pagination beyond available pages"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Get total pages
            response = client.get('/api/user', params={'page': 1, 'pageSize': 5})
            if response.status_code != 200 or not response.json_data:
                print("  ❌ Could not get total pages")
                return False
            
            total_pages = response.json_data['pagination']['totalPages']
            beyond_page = total_pages + 10
            
            print(f"  🔍 Testing beyond bounds: requesting page {beyond_page} (total: {total_pages})")
            
            response = client.get('/api/user', params={'page': beyond_page, 'pageSize': 5})
            
            # Should return 200 with empty data or handle gracefully
            if response.status_code == 200:
                data = response.json_data.get('data', [])
                print(f"  ✅ Beyond bounds handled gracefully: {len(data)} users returned")
                return True
            elif response.status_code == 404:
                print(f"  ✅ Beyond bounds returned 404 (acceptable)")
                return True
            else:
                print(f"  ❌ Unexpected status for beyond bounds: {response.status_code}")
                return False
            
        except Exception as e:
            print(f"  ❌ Exception in test_pagination_beyond_bounds: {e}")
            return False
    
    def test_invalid_pagination_parameters(self, config_file: str, curl: bool = False) -> bool:
        """Test invalid pagination parameters"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        test_cases = [
            {"page": 0, "pageSize": 10, "desc": "zero page"},
            {"page": -1, "pageSize": 10, "desc": "negative page"},
            {"page": 1, "pageSize": 0, "desc": "zero page size"},
            {"page": 1, "pageSize": -5, "desc": "negative page size"},
            {"page": "invalid", "pageSize": 10, "desc": "non-numeric page"},
            {"page": 1, "pageSize": "invalid", "desc": "non-numeric page size"},
        ]
        
        try:
            for case in test_cases:
                print(f"  🔍 Testing {case['desc']}: page={case['page']}, pageSize={case['pageSize']}")
                
                response = client.get('/api/user', params={'page': case['page'], 'pageSize': case['pageSize']})
                
                # Should either return error or default to valid values
                if response.status_code >= 400:
                    print(f"     ✅ Correctly returned error: {response.status_code}")
                elif response.status_code == 200:
                    print(f"     ✅ Invalid params handled with defaults")
                else:
                    print(f"     ❌ Unexpected status: {response.status_code}")
                    return False
            
            print(f"  ✅ Invalid pagination parameters handled correctly")
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_invalid_pagination_parameters: {e}")
            return False
    
    def test_large_page_size(self, config_file: str, curl: bool = False) -> bool:
        """Test very large page size"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            # Test with very large page size
            large_page_size = 1000
            
            print(f"  🔍 Testing large page size: {large_page_size}")
            
            response = client.get('/api/user', params={'page': 1, 'pageSize': large_page_size})
            
            # Should return 200 or handle with maximum limit
            if response.status_code != 200:
                print(f"  ❌ Large page size failed: {response.status_code}")
                return False
            
            is_valid, msg = ResponseValidator.validate_pagination_response(response)
            if not is_valid:
                print(f"  ❌ Response validation failed: {msg}")
                return False
            
            data = response.json_data
            users = data['data']
            pagination = data['pagination']
            
            # Check if page size was capped
            actual_page_size = pagination['pageSize']
            if actual_page_size != large_page_size:
                print(f"  ✅ Large page size capped: requested {large_page_size}, got {actual_page_size}")
            else:
                print(f"  ✅ Large page size accepted: {actual_page_size}")
            
            print(f"     Returned {len(users)} users")
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_large_page_size: {e}")
            return False
    
    def test_pagination_consistency(self, config_file: str, curl: bool = False) -> bool:
        """Test pagination consistency across multiple requests"""
        client = APIClient(verbose=self.verbose, curl_file="tests/curl.sh" if curl else None)
        
        try:
            page_size = 3
            
            # Get first two pages
            response1 = client.get('/api/user', params={'page': 1, 'pageSize': page_size})
            response2 = client.get('/api/user', params={'page': 2, 'pageSize': page_size})
            
            if response1.status_code != 200 or response2.status_code != 200:
                if response2.status_code == 404:
                    print("  ⚠️  Only one page available - consistency test limited")
                    return True
                print(f"  ❌ Requests failed: {response1.status_code}, {response2.status_code}")
                return False
            
            data1 = response1.json_data
            data2 = response2.json_data
            
            # Check total counts are consistent
            total1 = data1['pagination']['totalCount']
            total2 = data2['pagination']['totalCount']
            
            if total1 != total2:
                print(f"  ❌ Inconsistent total counts: {total1} vs {total2}")
                return False
            
            # Check no duplicate users between pages
            users1 = data1['data']
            users2 = data2['data']
            
            ids1 = set(user['_id'] for user in users1)
            ids2 = set(user['_id'] for user in users2)
            
            overlap = ids1.intersection(ids2)
            if overlap:
                print(f"  ❌ Duplicate users between pages: {overlap}")
                return False
            
            print(f"  ✅ Pagination consistency verified")
            print(f"     Page 1: {len(users1)} users, Page 2: {len(users2)} users")
            print(f"     Total count: {total1}, No overlaps")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Exception in test_pagination_consistency: {e}")
            return False
    
    def run_all_tests(self, config_file: str, curl: bool = False) -> bool:
        """Run all pagination tests with a specific config"""
        print(f"\n{'='*80}")
        print(f"PAGINATION TESTS")
        print(f"Config: {config_file}")
        print('='*80)
        
        tests = [
            ("Basic pagination", self.test_basic_pagination),
            ("Page boundaries", self.test_pagination_page_boundaries),
            ("Beyond bounds", self.test_pagination_beyond_bounds),
            ("Invalid parameters", self.test_invalid_pagination_parameters),
            ("Large page size", self.test_large_page_size),
            ("Pagination consistency", self.test_pagination_consistency),
        ]
        
        for test_name, test_func in tests:
            self.runner.run_test(test_name, test_func, config_file=config_file, curl=curl)
        
        return self.runner.print_summary()
    
    def run_4_mode_tests(self, curl: bool = False) -> bool:
        """Run all pagination tests across 4 modes"""
        print(f"\n{'='*80}")
        print(f"PAGINATION TESTS - ALL 4 MODES")
        print('='*80)
        
        tests = [
            ("Basic pagination", self.test_basic_pagination),
            ("Page boundaries", self.test_pagination_page_boundaries),
            ("Beyond bounds", self.test_pagination_beyond_bounds),
            ("Invalid parameters", self.test_invalid_pagination_parameters),
            ("Large page size", self.test_large_page_size),
            ("Pagination consistency", self.test_pagination_consistency),
        ]
        
        for test_name, test_func in tests:
            self.runner.run_4_mode_test(test_name, test_func)
        
        return self.runner.print_summary()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Pagination tests for User endpoints')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--all-modes', action='store_true',
                       help='Run tests across all 4 modes (MongoDB/ES with/without validation)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--curl', action='store_true', help='Generate curl.sh file')
    
    args = parser.parse_args()
    
    if not args.config and not args.all_modes:
        print("❌ Must specify either --config <file> or --all-modes")
        return 1
    
    if args.config and args.all_modes:
        print("❌ Cannot specify both --config and --all-modes")
        return 1
    
    suite = PaginationTestSuite(verbose=args.verbose)
    
    try:
        if args.all_modes:
            success = suite.run_4_mode_tests(curl=args.curl)
        else:
            success = suite.run_all_tests(args.config, curl=args.curl)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())