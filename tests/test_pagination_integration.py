#!/usr/bin/env python3
"""
Pagination and filtering integration tests.
Tests actual API endpoints with real server running.
Uses the same BaseTestFramework as user validation tests.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.base_test import BaseTestFramework

class PaginationIntegrationTester(BaseTestFramework):
    """Pagination and filtering integration test suite"""
    
    def __init__(self, config_file: str, server_url: str = "http://127.0.0.1:5500", verbose: bool = False, curl: bool = False):
        super().__init__(config_file, server_url, verbose, curl)
    
    def test_basic_pagination(self):
        """Test basic pagination parameters"""
        if self.verbose:
            print("\n🧪 Testing basic pagination...")
        
        success, response = self.make_api_request("GET", "/api/user?page=2&pageSize=15")
        if not success or 'data' not in response:
            return False
            
        # Just verify the request succeeded and we got a valid response structure
        data = response.get('data', [])
        return isinstance(data, list) and len(data) <= 15  # Data count should not exceed page size
    
    def test_sorting_parameters(self):
        """Test sorting parameters"""
        if self.verbose:
            print("\n🧪 Testing sorting parameters...")
            
        # Test ascending sort
        success, response = self.make_api_request("GET", "/api/user?sort=username&order=asc&pageSize=5")
        if not success or 'data' not in response:
            return False
            
        users = response['data']
        if len(users) < 2:
            return True  # Can't test sorting with < 2 users
            
        # Check if usernames are in ascending order
        usernames = [user.get('username', '') for user in users if 'username' in user]
        return usernames == sorted(usernames)
    
    def test_field_filtering(self):
        """Test field-based filtering"""
        if self.verbose:
            print("\n🧪 Testing field filtering...")
            
        # Test boolean field filtering (more likely to have data)
        success, response = self.make_api_request("GET", "/api/user?isAccountOwner=true&pageSize=10")
        if not success or 'data' not in response:
            return False
            
        # Just verify we got a valid response structure - filtering correctness tested elsewhere
        data = response.get('data', [])
        return isinstance(data, list)  # Valid response structure
    
    def test_text_search_filtering(self):
        """Test text search filtering (partial matching)"""
        if self.verbose:
            print("\n🧪 Testing text search filtering...")
            
        # Test partial text matching
        success, response = self.make_api_request("GET", "/api/user?username=test&pageSize=10")
        if not success:
            return False
            
        # If we get users, verify usernames contain 'test'
        users = response.get('data', [])
        if users:
            return all('test' in user.get('username', '').lower() for user in users if 'username' in user)
        return True  # No users matching filter is valid
    
    def test_range_filtering(self):
        """Test range filtering with bracket notation"""
        if self.verbose:
            print("\n🧪 Testing range filtering...")
            
        # Test range filtering on netWorth
        success, response = self.make_api_request("GET", "/api/user?netWorth=[1000:50000]&pageSize=10")
        if not success:
            return False
            
        # If we get users, verify they fall within range
        users = response.get('data', [])
        if users:
            for user in users:
                net_worth = user.get('netWorth')
                if net_worth is not None:
                    if not (1000 <= net_worth <= 50000):
                        return False
        return True
    
    def test_complex_filtering(self):
        """Test combination of multiple filters"""
        if self.verbose:
            print("\n🧪 Testing complex filtering...")
            
        # Test multiple filters combined
        url = "/api/user?gender=male&isAccountOwner=true&netWorth=[1000:]&pageSize=5"
        success, response = self.make_api_request("GET", url)
        if not success:
            return False
            
        # If we get users, verify they match all criteria
        users = response.get('data', [])
        if users:
            for user in users:
                if user.get('gender') != 'male':
                    return False
                if user.get('isAccountOwner') != True:
                    return False
                net_worth = user.get('netWorth')
                if net_worth is not None and net_worth < 1000:
                    return False
        return True
    
    def test_pagination_with_filtering(self):
        """Test pagination combined with filtering"""
        if self.verbose:
            print("\n🧪 Testing pagination with filtering...")
            
        # Get first page
        success1, response1 = self.make_api_request("GET", "/api/user?gender=male&page=1&pageSize=5")
        if not success1:
            return False
            
        # Get second page  
        success2, response2 = self.make_api_request("GET", "/api/user?gender=male&page=2&pageSize=5")
        if not success2:
            return False
            
        # Verify pagination metadata is consistent
        if response1.get('page_size') != response2.get('page_size'):
            return False
            
        # If both pages have data, verify no overlap
        users1 = response1.get('data', [])
        users2 = response2.get('data', [])
        
        if users1 and users2:
            ids1 = {user.get('id') for user in users1 if 'id' in user}
            ids2 = {user.get('id') for user in users2 if 'id' in user}
            return len(ids1.intersection(ids2)) == 0  # No overlap
            
        return True
    
    def test_error_handling(self):
        """Test error handling for invalid parameters"""
        if self.verbose:
            print("\n🧪 Testing error handling...")
            
        # Test invalid page number - should still return valid response
        success, response = self.make_api_request("GET", "/api/user?page=0&pageSize=10")
        # Should succeed and return valid data structure regardless of parameter correction
        return success and 'data' in response and isinstance(response['data'], list)
    
    def test_empty_results(self):
        """Test handling of filters that return no results"""
        if self.verbose:
            print("\n🧪 Testing empty results...")
            
        # Use a filter that's unlikely to match anything
        success, response = self.make_api_request("GET", "/api/user?username=nonexistentuser12345")
        if not success:
            return False
            
        # Should return empty data array but valid structure
        return ('data' in response and 
                isinstance(response['data'], list) and 
                len(response['data']) == 0)

    @staticmethod
    def create_argument_parser():
        """Create argument parser for pagination tests"""
        import argparse
        parser = argparse.ArgumentParser(description='Pagination Integration Testing Framework')
        parser.add_argument('config_file', nargs='?', default='mongo.json',
                           help='Configuration file path (default: mongo.json)')
        parser.add_argument('--server-url', default='http://127.0.0.1:5500',
                           help='Server URL for API tests (default: http://127.0.0.1:5500)')
        parser.add_argument('--preserve', action='store_true',
                           help='Preserve test data after running tests (for troubleshooting)')
        parser.add_argument('--verbose', action='store_true',
                           help='Show detailed URL testing and response information')
        parser.add_argument('--curl', action='store_true',
                           help='Dump all API calls in curl format to curl.sh (overwrites existing file)')
        parser.add_argument('--api', action='store_true',
                           help='Run only basic API tests (excludes pagination/filtering)')
        parser.add_argument('--pfs', action='store_true',
                           help='Run only pagination/filtering/sorting tests')
        return parser

async def main():
    """Run pagination integration tests"""
    parser = PaginationIntegrationTester.create_argument_parser()
    args = parser.parse_args()
    
    # Determine which tests to run
    run_api = args.api or (not args.api and not args.pfs)  # Default includes API
    run_pfs = args.pfs or (not args.api and not args.pfs)  # Default includes PFS
    
    test_mode = []
    if run_api:
        test_mode.append("API")
    if run_pfs:
        test_mode.append("PFS")
    
    print("🚀 Starting Pagination Integration Tests")
    print(f"Config: {args.config_file}")
    print(f"Server: {args.server_url}")
    print(f"Mode: {' + '.join(test_mode)} tests")
    print("="*60)
    
    tester = PaginationIntegrationTester(args.config_file, args.server_url, args.verbose, args.curl)
    
    # Setup database connection
    if not await tester.setup_database_connection():
        print("❌ Failed to setup database connection")
        return False
    
    try:
        # Run API tests if requested
        if run_api:
            print("\n🔧 API TESTS")
            print("-" * 30)
            tester.test("Error Handling", tester.test_error_handling, True)
            tester.test("Empty Results", tester.test_empty_results, True)
        
        # Run PFS tests if requested
        if run_pfs:
            print("\n🔍 PAGINATION/FILTERING/SORTING TESTS")
            print("-" * 45)
            tester.test("Basic Pagination", tester.test_basic_pagination, True)
            tester.test("Sorting Parameters", tester.test_sorting_parameters, True) 
            tester.test("Field Filtering", tester.test_field_filtering, True)
            tester.test("Text Search Filtering", tester.test_text_search_filtering, True)
            tester.test("Range Filtering", tester.test_range_filtering, True)
            tester.test("Complex Filtering", tester.test_complex_filtering, True)
            tester.test("Pagination with Filtering", tester.test_pagination_with_filtering, True)
        
        # Print summary
        success = tester.summary()
        return success
        
    finally:
        # Always cleanup database connection
        await tester.cleanup_database_connection()

if __name__ == "__main__":
    print("Pagination Integration Test Suite")
    print("Usage: python test_pagination_integration.py [config_file] [options]")
    print("Options:")
    print("  --api     Run only basic API tests")
    print("  --pfs     Run only pagination/filtering/sorting tests")
    print("  --verbose Show detailed URL output")
    print("Example: python test_pagination_integration.py mongo.json --pfs --verbose")
    print()
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        sys.exit(1)