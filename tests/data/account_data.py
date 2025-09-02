"""
Account entity data generation - combines fixed test scenarios with dynamic generation.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple, Optional
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from .datagen import DataGen


class AccountDataFactory:
    """Data generation for Account entity - combines fixed scenarios with dynamic generation"""
    
    # Static test scenarios
    test_scenarios = [
        {
            "id": "507f1f77bcf86cd799439011",
            "name": "Test Account",
            "createdAt": "2023-01-01T00:00:00Z",
            "expiredAt": "2025-12-31T23:59:59Z"
        }
    ]
    
    @staticmethod
    def get_test_record_by_id(record_id: str) -> Optional[Dict]:
        """Get test record by ID"""
        for record in AccountDataFactory.test_scenarios:
            if record.get('id') == record_id:
                return record
        return None
    
    @staticmethod
    def generate_data():
        """Generate random account data and add to test scenarios"""
        datagen = DataGen(entity="account")
        random_valid, random_invalid = datagen.generate_records(
            good_count=10,
            bad_count=5, 
            include_known_test_records=False
        )
        
        # Add random records to test scenarios
        for record in random_valid + random_invalid:
            AccountDataFactory.test_scenarios.append(record)
    
    
    
    @staticmethod
    def _create_known_test_records() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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