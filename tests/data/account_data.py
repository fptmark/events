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

from . import BaseDataFactory
from .datagen import DataGen


class AccountDataFactory(BaseDataFactory):
    """Data generation for Account entity - combines fixed scenarios with dynamic generation"""
    
    @staticmethod
    def generate_data() -> Tuple[List[Dict], List[Dict]]:
        """Generate ALL account data (fixed + random) - Account factory controls its own counts"""
        # Get fixed test scenarios
        fixed_valid, fixed_invalid = AccountDataFactory._create_known_test_records()
        
        # Generate random records using DataGen - Account-specific counts (fewer than users)
        datagen = DataGen(entity="account")
        random_valid, random_invalid = datagen.generate_records(
            good_count=10,  # Account factory decides fewer accounts than users
            bad_count=5, 
            include_known_test_records=False  # We already have fixed records
        )
        
        # Combine fixed + random
        all_valid = fixed_valid + random_valid
        all_invalid = fixed_invalid + random_invalid
        
        return all_valid, all_invalid
    
    @staticmethod
    def get_test_scenarios() -> Dict[str, Dict]:
        """Get test scenarios for this entity - reuse existing test records"""
        valid_records, invalid_records = AccountDataFactory._create_known_test_records()
        scenarios = {}
        
        # Convert list of records to dict keyed by ID
        for record in valid_records + invalid_records:
            scenarios[record['id']] = record
            
        return scenarios
    
    @staticmethod
    def get_test_record_by_id(record_id: str) -> Optional[Dict]:
        """Use base class universal lookup"""
        return BaseDataFactory.get_test_record_by_id(record_id)
    
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