#!/usr/bin/env python3
"""
Fixed test records for Account entity.
Creates specific known test records that the test framework expects.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple

class FixedAccounts:
    """Creates specific known test records for Account entity."""
    
    @staticmethod
    def create_known_test_records() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Create specific known test accounts that the test framework expects."""
        valid_records = []
        invalid_records = []
        
        # Base timestamp for consistency
        base_time = datetime.now(timezone.utc)
        future_time = base_time + timedelta(days=365)
        past_time = base_time - timedelta(days=30)
        
        # Known test account scenarios
        test_scenarios = {
            # Valid test accounts
            "primary_account_123456": {
                "id": "primary_account_123456",
                "name": "Primary Test Account",
                "createdAt": base_time,
                "updatedAt": base_time,
                "expiredAt": future_time  # Valid: expires in future
            },
            
            "secondary_account_123456": {
                "id": "secondary_account_123456", 
                "name": "Secondary Test Account",
                "createdAt": base_time,
                "updatedAt": base_time,
                "expiredAt": None  # Valid: no expiration
            },
            
            # Invalid test accounts
            "expired_account_123456": {
                "id": "expired_account_123456",
                "name": "Expired Test Account",
                "createdAt": base_time,
                "updatedAt": base_time,
                "expiredAt": past_time  # Invalid: already expired
            },
            
            "bad_dates_account_123456": {
                "id": "bad_dates_account_123456",
                "name": "Bad Dates Account",
                "createdAt": future_time,  # Invalid: created in future
                "updatedAt": base_time,
                "expiredAt": past_time     # Invalid: expired before creation
            }
        }
        
        # Categorize into valid vs invalid based on validation issues
        for account_id, account_data in test_scenarios.items():
            if "expired_" in account_id or "bad_" in account_id:
                invalid_records.append(account_data)
            else:
                valid_records.append(account_data)
        
        return valid_records, invalid_records

# Test account constants for easy reference in test cases
TEST_ACCOUNTS = {
    "primary": "primary_account_123456",
    "secondary": "secondary_account_123456"
}