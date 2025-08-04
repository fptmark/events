#!/usr/bin/env python3
"""
Fixed test records for User entity.
Creates specific known test records that the test framework expects.
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple

class FixedUsers:
    """Creates specific known test records for User entity."""
    
    @staticmethod
    def create_known_test_records() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Create specific known test users that the test framework expects."""
        valid_records = []
        invalid_records = []
        
        # Base timestamp for consistency
        base_time = datetime.now()
        
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
                "createdAt": base_time.isoformat(),
                "updatedAt": base_time.isoformat()
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
                "createdAt": base_time.isoformat(),
                "updatedAt": base_time.isoformat()
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
                "createdAt": base_time.isoformat(),
                "updatedAt": base_time.isoformat()
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
                "createdAt": base_time.isoformat(),
                "updatedAt": base_time.isoformat()
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
                "createdAt": base_time.isoformat(),
                "updatedAt": base_time.isoformat()
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
                "createdAt": base_time.isoformat(),
                "updatedAt": base_time.isoformat()
            }
        }
        
        # Categorize into valid vs invalid based on validation issues
        for user_id, user_data in test_scenarios.items():
            if "bad_" in user_id or "multiple_errors" in user_id:
                invalid_records.append(user_data)
            else:
                valid_records.append(user_data)
        
        return valid_records, invalid_records