#!/usr/bin/env python3
"""
Simple pagination and filtering test suite.

Tests the basic functionality without requiring pytest:
- ListParams URL parameter parsing
- Range bracket notation parsing
- MongoDB query generation
- API integration (mocked)

Usage:
    python tests/test_pagination_simple.py
    python tests/test_pagination_simple.py config.json
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.list_params import ListParams


class PaginationTester:
    """Simple test class for pagination functionality."""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def assert_equal(self, actual, expected, test_name):
        """Simple assertion helper."""
        if actual == expected:
            self.tests_passed += 1
            self.test_results.append(f"✅ {test_name}")
            return True
        else:
            self.tests_failed += 1
            self.test_results.append(f"❌ {test_name}")
            print(f"  FAILED: Expected {expected}, got {actual}")
            return False
    
    def test_basic_pagination_parsing(self):
        """Test basic pagination parameter parsing."""
        print("\n📝 Testing basic pagination parsing...")
        
        query_params = {
            "page": "3",
            "pageSize": "50", 
            "sort": "name",
            "order": "desc"
        }
        params = ListParams.from_query_params(query_params)
        
        self.assert_equal(params.page, 3, "Page number parsing")
        self.assert_equal(params.page_size, 50, "Page size parsing")
        self.assert_equal(params.sort_field, "name", "Sort field parsing")
        self.assert_equal(params.sort_order, "desc", "Sort order parsing")
        self.assert_equal(params.skip, 100, "Skip calculation")
    
    def test_field_filters_parsing(self):
        """Test field filter parameter parsing."""
        print("\n🔍 Testing field filter parsing...")
        
        query_params = {
            "username": "john",
            "email": "gmail", 
            "firstName": "John"
        }
        params = ListParams.from_query_params(query_params)
        
        expected_filters = {
            "username": "john",
            "email": "gmail",
            "firstName": "John"
        }
        self.assert_equal(params.filters, expected_filters, "Field filters parsing")
    
    def test_range_filters_full(self):
        """Test range filters with both min and max."""
        print("\n📊 Testing range filter parsing...")
        
        query_params = {
            "age": "[18:65]",
            "netWorth": "[50000:100000]",
            "score": "[75.5:95.5]"
        }
        params = ListParams.from_query_params(query_params)
        
        self.assert_equal(params.filters["age"], {"$gte": 18, "$lte": 65}, "Age range filter")
        self.assert_equal(params.filters["netWorth"], {"$gte": 50000, "$lte": 100000}, "NetWorth range filter")
        self.assert_equal(params.filters["score"], {"$gte": 75.5, "$lte": 95.5}, "Score range filter")
    
    def test_range_filters_partial(self):
        """Test range filters with min or max only."""
        print("\n📈 Testing partial range filters...")
        
        # Min only
        query_params = {"age": "[21:]", "netWorth": "[45000:]"}
        params = ListParams.from_query_params(query_params)
        
        self.assert_equal(params.filters["age"], {"$gte": 21}, "Min-only age filter")
        self.assert_equal(params.filters["netWorth"], {"$gte": 45000}, "Min-only netWorth filter")
        
        # Max only
        query_params = {"age": "[:65]", "netWorth": "[:75000]"}
        params = ListParams.from_query_params(query_params)
        
        self.assert_equal(params.filters["age"], {"$lte": 65}, "Max-only age filter")
        self.assert_equal(params.filters["netWorth"], {"$lte": 75000}, "Max-only netWorth filter")
    
    def test_exact_match_filters(self):
        """Test exact match field filters."""
        print("\n🎯 Testing exact match filters...")
        
        query_params = {
            "gender": "male",
            "age": "25",
            "netWorth": "89000.5"
        }
        params = ListParams.from_query_params(query_params)
        
        self.assert_equal(params.filters["gender"], "male", "String exact match")
        self.assert_equal(params.filters["age"], 25, "Integer exact match")
        self.assert_equal(params.filters["netWorth"], 89000.5, "Float exact match")
    
    def test_mongo_query_generation(self):
        """Test MongoDB query generation through driver."""
        print("\n🗄️ Testing MongoDB query generation...")
        
        # Import MongoDB driver for testing
        from app.db.mongodb import MongoDatabase
        
        params = ListParams()
        params.filters = {
            "username": "john",
            "email": "gmail", 
            "gender": "male",
            "age": {"$gte": 18, "$lte": 65},
            "netWorth": {"$gte": 50000}
        }
        
        # Create User model metadata for field type lookup
        from app.models.user_model import User
        user_metadata = User._metadata
        
        db = MongoDatabase()
        query = db._build_query_filter(params, user_metadata)
        expected = {
            "username": {"$regex": ".*john.*", "$options": "i"},
            "email": {"$regex": ".*gmail.*", "$options": "i"},
            "gender": "male",  # Enum - exact match
            "age": {"$gte": 18, "$lte": 65},
            "netWorth": {"$gte": 50000}
        }
        
        self.assert_equal(query, expected, "MongoDB query generation")
    
    def test_mongo_sort_generation(self):
        """Test MongoDB sort specification generation."""
        print("\n🔄 Testing MongoDB sort generation...")
        
        from app.db.mongodb import MongoDatabase
        
        # Test descending sort
        params = ListParams()
        params.sort_field = "username"
        params.sort_order = "desc"
        
        db = MongoDatabase()
        sort_spec = db._build_sort_spec(params)
        self.assert_equal(sort_spec, {"username": -1}, "Descending sort")
        
        # Test ascending sort
        params.sort_order = "asc"
        sort_spec = db._build_sort_spec(params)
        self.assert_equal(sort_spec, {"username": 1}, "Ascending sort")
        
        # Test no sort field
        params.sort_field = None
        sort_spec = db._build_sort_spec(params)
        self.assert_equal(sort_spec, {}, "No sort field")
    
    def test_complex_url_parsing(self):
        """Test parsing complex URL with all parameter types."""
        print("\n🌐 Testing complex URL parsing...")
        
        query_params = {
            "page": "2",
            "pageSize": "15",
            "sort": "createdAt",
            "order": "desc", 
            "username": "john",
            "email": "gmail.com",
            "gender": "male",
            "age": "[25:45]",
            "netWorth": "[50000:]",
            "score": "[:90]"
        }
        params = ListParams.from_query_params(query_params)
        
        self.assert_equal(params.page, 2, "Complex URL - page")
        self.assert_equal(params.page_size, 15, "Complex URL - pageSize")
        self.assert_equal(params.sort_field, "createdAt", "Complex URL - sort field")
        self.assert_equal(params.sort_order, "desc", "Complex URL - sort order")
        self.assert_equal(params.skip, 15, "Complex URL - skip calculation")
        
        expected_filters = {
            "username": "john",
            "email": "gmail.com",
            "gender": "male",
            "age": {"$gte": 25, "$lte": 45},
            "netWorth": {"$gte": 50000},
            "score": {"$lte": 90}
        }
        self.assert_equal(params.filters, expected_filters, "Complex URL - all filters")
    
    def test_error_handling(self):
        """Test error handling for invalid parameters."""
        print("\n⚠️ Testing error handling...")
        
        # This should trigger notification system but not crash
        query_params = {
            "page": "0",  # Invalid: must be >= 1
            "pageSize": "2000",  # Invalid: exceeds max
            "order": "invalid",  # Invalid: must be asc/desc
            "age": "[invalid:65]",  # Invalid: non-numeric range
        }
        
        try:
            params = ListParams.from_query_params(query_params)
            # Should have corrected invalid values
            self.assert_equal(params.page, 1, "Error handling - page corrected")
            self.assert_equal(params.page_size, 1000, "Error handling - pageSize capped")
            self.assert_equal(params.sort_order, "asc", "Error handling - order corrected")
            print("✅ Error handling works - invalid params corrected")
        except Exception as e:
            print(f"❌ Error handling failed: {e}")
            self.tests_failed += 1
    
    def run_all_tests(self):
        """Run all tests."""
        print("🧪 PAGINATION/FILTERING TESTS")
        print("=" * 50)
        
        try:
            self.test_basic_pagination_parsing()
            self.test_field_filters_parsing() 
            self.test_range_filters_full()
            self.test_range_filters_partial()
            self.test_exact_match_filters()
            self.test_mongo_query_generation()
            self.test_mongo_sort_generation()
            self.test_complex_url_parsing()
            self.test_error_handling()
            
        except Exception as e:
            print(f"\n❌ Test suite crashed: {e}")
            self.tests_failed += 1
        
        # Print summary
        print(f"\n📊 TEST SUMMARY")
        print("=" * 30)
        total_tests = self.tests_passed + self.tests_failed
        print(f"Total tests: {total_tests}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_failed}")
        print(f"Success rate: {(self.tests_passed / total_tests * 100):.1f}%" if total_tests > 0 else "No tests run")
        
        if self.tests_failed == 0:
            print("\n🎉 All tests passed!")
            return True
        else:
            print(f"\n💥 {self.tests_failed} test(s) failed")
            print("\nFailed tests:")
            for result in self.test_results:
                if result.startswith("❌"):
                    print(f"  {result}")
            return False


def main():
    """Main test runner."""
    config_file = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith('.json') else None
    
    if config_file and os.path.exists(config_file):
        print(f"📋 Using configuration: {config_file}")
        os.environ['CONFIG_FILE'] = config_file
    else:
        print("📋 Using default configuration")
    
    tester = PaginationTester()
    success = tester.run_all_tests()
    
    return success


if __name__ == "__main__":
    print("Pagination/Filtering Test Suite")
    print("Usage: python test_pagination_simple.py [config_file]")
    print("Example: python test_pagination_simple.py mongo.json")
    print()
    
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)