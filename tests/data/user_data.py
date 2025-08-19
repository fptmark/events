"""
User entity data generation - combines fixed test scenarios with dynamic generation.
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from .datagen import DataGen


class UserDataFactory:
    """Data generation for User entity - combines fixed scenarios with dynamic generation"""
    
    # Static storage for initialized data
    # Known test user scenarios based on what the test framework expects
    test_scenarios = {
        # Valid test users
        "valid_all_user_123456": {
            "id": "valid_all_user_123456",
            "username": "valid_all_user", 
            "email": "valid_all@test.com",
            "firstName": "Valid",
            "lastName": "User",
            "gender": "male",  # Valid enum
            "netWorth": 50000.0,  # Valid currency
            "isAccountOwner": True,
            "dob": "1985-06-15",  # Date for sorting/filtering tests
        },
        
        "valid_fk_only_user_123456": {
            "id": "valid_fk_only_user_123456", 
            "username": "valid_fk_user",
            "email": "valid_fk@test.com",
            "firstName": "ValidFK",
            "lastName": "User",
            "gender": "female",  # Valid enum
            "netWorth": 75000.0,  # Valid currency
            "isAccountOwner": False,
            "dob": "1992-03-20",  # Different decade for range tests
        },
        
        # Invalid test users (for validation testing)
        "bad_enum_user_123456": {
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
        
        "bad_currency_user_123456": {
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
        
        "bad_fk_user_123456": {
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
        
        "multiple_errors_user_123456": {
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
    }

    
    @staticmethod
    def get_test_record_by_id(record_id: str) -> Optional[Dict]:
        """Get test record by ID"""
        return UserDataFactory.test_scenarios.get(record_id)
    
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
            UserDataFactory.test_scenarios[record['id']] = record