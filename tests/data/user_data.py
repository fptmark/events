"""
User entity data generation - combines fixed test scenarios with dynamic generation.
"""

from typing import Dict, Any, List, Tuple, Optional

# Add project root to path
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# sys.path.insert(0, str(Path(__file__).parent.parent))

from .datagen import DataGen


class UserDataFactory:
    """Data generation for User entity - combines fixed scenarios with dynamic generation"""
    
    # Static storage for initialized data
    # Known test user scenarios based on what the test framework expects
    test_scenarios = [
        # Valid test users
        {
            "id": "valid_user_1",
            "username": "valid_all_user", 
            "email": "valid_all@test.com",
            "firstName": "Valid",
            "lastName": "User",
            "password": "ValidPass123!",  # Valid password
            "accountId": "primary_account_123456",  # Valid FK to existing account
            "gender": "male",  # Valid enum
            "netWorth": 50000.0,  # Valid currency
            "isAccountOwner": True,
            "dob": "1985-06-15",  # Date for sorting/filtering tests
            "createdAt": "2023-01-01T12:00:00Z",
            "updatedAt": "2023-06-01T12:00:00Z"
        },
        
        {
            "id": "missing_pwd_acct_3456",
            "username": "valid_all_user", 
            "email": "valid_all@test.com",
            "firstName": "Valid",
            "lastName": "User",
            "gender": "male",  # Valid enum
            "netWorth": 50000.0,  # Valid currency
            "isAccountOwner": True,
            "dob": "1985-06-15",  # Date for sorting/filtering tests
        },
        
        # Invalid test users (for validation testing)
        {
            "id": "bad_enum_user_123456",
            "username": "bad_enum_user",
            "email": "bad_enum@test.com", 
            "firstName": "BadEnum",
            "lastName": "User",
            "gender": "invalid_gender",  # Invalid enum
            "netWorth": 50000.0,  # Valid currency
            "isAccountOwner": True,
            "dob": "1978-11-08",  # Earlier decade for comprehensive range tests
        },
        
        {
            "id": "bad_currency_user_123456",
            "username": "bad_currency_user",
            "email": "bad_currency@test.com",
            "firstName": "BadCurrency", 
            "lastName": "User",
            "gender": "male",  # Valid enum
            "netWorth": -5000.0,  # Invalid currency (negative)
            "isAccountOwner": True,
            "dob": "2001-12-25",  # 2000s for more recent date testing
        },
        
        {
            "id": "bad_fk_user_123456",
            "username": "bad_fk_user", 
            "email": "bad_fk@test.com",
            "firstName": "BadFK",
            "lastName": "User",
            "gender": "female",  # Valid enum
            "netWorth": 75000.0,  # Valid currency
            "accountId": "nonexistent_account_123456",  # Invalid FK
            "isAccountOwner": False,
            "dob": "1995-04-10",  # Mid-90s for good date range coverage
        },
        
        {
            "id": "multiple_errors_user_123456",
            "username": "multiple_errors_user",
            "email": "multiple_errors@test.com",
            "firstName": "MultipleErrors",
            "lastName": "User", 
            "gender": "bad_value",  # Invalid enum
            "netWorth": -10000.0,  # Invalid currency
            "accountId": "nonexistent_account_456789",  # Invalid FK
            "isAccountOwner": False,
            "dob": "1988-09-14",  # Late 80s for comprehensive decade coverage
        }
    ]

    @classmethod
    def get_test_cases(cls):
        """Return TestCase objects for basic CRUD operations"""
        from tests.suites.test_case import TestCase
        
        return [
            TestCase("GET", "User", "valid_user_1", '', "Get Valid user", 200),
            TestCase("GET", "User", "missing_pwd_acct_3456", '', "Missing pwd and accountId fields", 200),
            TestCase("GET", "User", "bad_enum_user_123456", '', "Get user with bad enum", 200),
            TestCase("GET", "User", "bad_currency_user_123456", '', "Get user with bad currency", 200),
            TestCase("GET", "User", "bad_fk_user_123456", '', "Get user with bad FK", 200),
            TestCase("GET", "User", "multiple_errors_user_123456", '', "Get user with multiple errors", 200),
            TestCase("GET", "User", "nonexistent_user_123456", '', "Get non-existent user", 404),
            TestCase("GET", "User", '', '', "Get user list", 200),
            TestCase("GET", "user", '', "pageSize=3", "Get user list with page size", 200)
        ]

    @staticmethod
    def get_test_record_by_id(record_id: str) -> Optional[Dict]:
        """Get test record by ID"""
        for record in UserDataFactory.test_scenarios:
            if record.get('id') == record_id:
                return record
        return None
    
    @staticmethod
    def generate_data():
        """Generate random user data and add to test scenarios"""
        datagen = DataGen(entity="user")
        random_valid, random_invalid = datagen.generate_records(
            good_count=50,
            bad_count=20, 
            include_known_test_records=False
        )
        # Add random records to test scenarios
        for record in random_valid + random_invalid:
            UserDataFactory.test_scenarios.append(record)