#!/usr/bin/env python3
"""
Test Data Setup Utility

Creates test entities with known validation issues for comprehensive validation testing.
Inserts data directly via DatabaseFactory to bypass model validation.
"""

import sys
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config
from app.db import DatabaseFactory

class TestDataCreator:
    def __init__(self):
        self.test_user_ids = []
        self.test_account_ids = []
    
    async def setup_database(self, config_file: str = "mongo.json"):
        """Initialize database connection"""
        config = Config.initialize(config_file)
        db_type = config.get('database')
        db_uri = config.get('db_uri')
        db_name = config.get('db_name')
        
        if db_type and db_uri and db_name:
            print(f"📂 Connecting to {db_type} at {db_uri}/{db_name}")
            await DatabaseFactory.initialize(db_type, db_uri, db_name)
            print("✅ Database connection established")
        else:
            print("❌ Bad database config ... quitting")
    
    async def cleanup_database(self):
        """Close database connection"""
        if DatabaseFactory.is_initialized():
            await DatabaseFactory.close()
            print("✅ Database connection closed")
    
    async def create_test_account(self, account_suffix: str = "123456") -> str:
        """Create a test account and return its ID"""
        # Use predictable test ID that matches what the test framework expects
        account_id = f"valid_account_{account_suffix}"
        
        account_doc = {
            "id": account_id,
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc),
            "expiredAt": None  # Optional field from account model
        }
        
        result, warnings = await DatabaseFactory.save_document("account", account_doc, [])
        if warnings:
            print(f"⚠️ Account creation warnings: {warnings}")
        
        self.test_account_ids.append(account_id)
        print(f"✅ Created test account: {account_id}")
        return account_id
    
    async def create_test_user(self, scenario: str, account_id: str) -> str:
        """Create a test user with specific validation issues or valid data"""
        # Use predictable test IDs that match what the test framework expects
        user_id = f"{scenario}_user_123456"
        base_time = datetime.now(timezone.utc)
        
        # Base valid user data
        user_doc = {
            "id": user_id,
            "username": f"testuser_{scenario}_{user_id[:8]}",
            "email": f"test_{scenario}@example.com",
            "password": "securepassword123",
            "firstName": "Test",
            "lastName": "User",
            "isAccountOwner": True,
            "createdAt": base_time,
            "updatedAt": base_time
        }
        
        # Add specific validation issues or valid data based on scenario
        if scenario == "valid_all":
            user_doc["gender"] = "male"  # Valid
            user_doc["netWorth"] = 50000.0  # Valid
            user_doc["accountId"] = account_id  # Valid FK
            
        elif scenario == "valid_fk_only":
            user_doc["gender"] = "female"  # Valid
            user_doc["netWorth"] = 75000.0  # Valid
            user_doc["accountId"] = account_id  # Valid FK
            
        elif scenario == "bad_enum":
            user_doc["gender"] = "invalid_gender"  # Invalid enum
            user_doc["netWorth"] = 50000.0  # Valid
            user_doc["accountId"] = account_id  # Valid FK
            
        elif scenario == "bad_currency":
            user_doc["gender"] = "male"  # Valid
            user_doc["netWorth"] = -5000.0  # Invalid: must be >= 0
            user_doc["accountId"] = account_id  # Valid FK
            
        elif scenario == "bad_fk":
            user_doc["gender"] = "female"  # Valid
            user_doc["netWorth"] = 75000.0  # Valid
            user_doc["accountId"] = account_id  # Invalid: FK doesn't exist (passed as nonexistent ID)
            
        elif scenario == "multiple_errors":
            user_doc["gender"] = "bad_value"  # Invalid enum
            user_doc["netWorth"] = -10000.0  # Invalid currency
            user_doc["accountId"] = account_id  # Invalid FK (passed as nonexistent ID)
            
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
        
        # Insert directly via DatabaseFactory (bypasses model validation)
        result, warnings = await DatabaseFactory.save_document("user", user_doc, [])
        if warnings:
            print(f"⚠️ User creation warnings: {warnings}")
        
        self.test_user_ids.append(user_id)
        print(f"✅ Created test user ({scenario}): {user_id}")
        return user_id
    
    async def create_comprehensive_test_data(self) -> Dict[str, str]:
        """Create all test data needed for comprehensive validation testing"""
        
        print("🧪 Creating comprehensive test data...")
        
        # 1. Create multiple valid accounts for FK references
        primary_account_id = await self.create_test_account("primary")
        secondary_account_id = await self.create_test_account("secondary")
        
        # 2. Create users with different validation scenarios
        test_users = {}
        
        # Test scenarios with comprehensive FK coverage
        scenarios = [
            # Valid scenarios for successful FK resolution testing
            ("valid_all", primary_account_id),         # All fields valid, FK should resolve
            ("valid_fk_only", secondary_account_id),   # Only FK valid, should still resolve FK
            
            # Invalid field scenarios but valid FK (FK should still resolve)
            ("bad_enum", primary_account_id),          # Invalid gender but valid FK
            ("bad_currency", primary_account_id),      # Invalid netWorth but valid FK
            
            # Invalid FK scenarios (FK should show exists: false)
            ("bad_fk", None),                          # Invalid FK only
            ("multiple_errors", None)                  # Multiple errors including invalid FK
        ]
        
        for scenario, account_id in scenarios:
            # For bad FK scenarios, pass a non-existent account ID
            if account_id is None:
                account_id = f"nonexistent_{scenario}_123456789012"
            user_id = await self.create_test_user(scenario, account_id)
            test_users[scenario] = user_id
        
        print(f"\n📊 Test data summary:")
        print(f"   Primary account: {primary_account_id}")
        print(f"   Secondary account: {secondary_account_id}")
        for scenario, user_id in test_users.items():
            print(f"   User ({scenario}): {user_id}")
        
        print(f"\n🎯 FK Testing Coverage:")
        print(f"   Users with VALID FKs: valid_all, valid_fk_only, bad_enum, bad_currency")
        print(f"   Users with INVALID FKs: bad_fk, multiple_errors")
        print(f"   This allows testing view parameters with both existing and non-existing FK references")
        
        return {
            "primary_account_id": primary_account_id,
            "secondary_account_id": secondary_account_id,
            **test_users
        }
    
    async def cleanup_test_data(self):
        """Remove all created test data"""
        print("🧹 Cleaning up test data...")
        
        # Delete test users
        for user_id in self.test_user_ids:
            try:
                success = await DatabaseFactory.delete_document("user", user_id)
                if success:
                    print(f"   ✅ Deleted user: {user_id}")
                else:
                    print(f"   ⚠️ Failed to delete user: {user_id}")
            except Exception as e:
                print(f"   ❌ Error deleting user {user_id}: {e}")
        
        # Delete test accounts
        for account_id in self.test_account_ids:
            try:
                success = await DatabaseFactory.delete_document("account", account_id)
                if success:
                    print(f"   ✅ Deleted account: {account_id}")
                else:
                    print(f"   ⚠️ Failed to delete account: {account_id}")
            except Exception as e:
                print(f"   ❌ Error deleting account {account_id}: {e}")
        
        print("✅ Test data cleanup complete")
    
    async def wipe_all_test_data(self):
        """Remove ALL data from database - use with caution!"""
        from app.metadata import get_all_entity_names
        
        print("💥 WIPING ALL DATA - This will remove ALL data from all collections!")
        
        try:
            # First, wipe all ES index templates to avoid conflicts
            await DatabaseFactory.wipe_all_index_templates()
            print("   🗑️ Wiped all ES index templates")
            
            # Then delete all application indices to force recreation with new templates
            await DatabaseFactory.wipe_all_indices()
            print("   🗑️ Deleted all application indices")
            
            # Get all registered entity names from metadata
            entity_names = get_all_entity_names()
            if not entity_names:
                # Fallback to known entities if metadata not loaded
                entity_names = ["User", "Account", "Profile", "TagAffinity", "Event", "UserEvent", "Url", "Crawl"]
            
            total_deleted = {}
            
            # Wipe ALL records from each entity collection
            for entity_name in entity_names:
                collection_name = entity_name.lower()
                
                all_docs, warnings, count = await DatabaseFactory.get_all(collection_name, [])
                deleted_count = 0
                
                for doc in all_docs:
                    doc_id = doc.get('id')
                    if doc_id:
                        success = await DatabaseFactory.delete_document(collection_name, doc_id)
                        if success:
                            deleted_count += 1
                
                if deleted_count > 0:
                    total_deleted[entity_name] = deleted_count
                    print(f"   🗑️ Deleted {deleted_count} {entity_name} records")
            
            deleted_summary = ', '.join([f"{count} {entity}" for entity, count in total_deleted.items()])
            print(f"✅ Database wipe complete: {deleted_summary}")
            
        except Exception as e:
            print(f"❌ Database wipe failed: {e}")
            raise

async def main():
    """Standalone test data creation"""
    import argparse
    parser = argparse.ArgumentParser(description='Test Data Setup')
    parser.add_argument('--config', default='mongo.json',
                       help='Config file (default: mongo.json)')
    parser.add_argument('--newdata', action='store_true',
                       help='Wipe existing data and create fresh test data')
    parser.add_argument('--wipe', action='store_true', 
                       help='DESTRUCTIVE: Wipe all test data and exit')
    args = parser.parse_args()
    
    # Validate arguments
    if args.newdata and args.wipe:
        print("❌ ERROR: Cannot use --newdata and --wipe together")
        return 1
    
    if not args.newdata and not args.wipe:
        print("❌ ERROR: Must specify either --newdata or --wipe")
        return 1
    
    creator = TestDataCreator()
    
    try:
        await creator.setup_database(args.config)
        
        if args.newdata:
            # Wipe existing test data first
            await creator.wipe_all_test_data()
            
            # Create fresh test data
            test_data = await creator.create_comprehensive_test_data()
            print(f"\n🎯 Fresh test data created successfully!")
            print("\n📋 Use these IDs in your validation tests:")
            for key, value in test_data.items():
                print(f"  {key}: {value}")
            print(f"\n🔍 View parameter testing scenarios:")
            print(f"  1. Test ?view={{\"account\":[\"createdAt\"]}} with valid FK users (should show account data)")
            print(f"  2. Test ?view={{\"account\":[\"createdAt\"]}} with invalid FK users (should show exists: false)")
            print(f"  3. Compare results with and without view parameters for comprehensive FK testing")
                
        elif args.wipe:
            await creator.wipe_all_test_data()
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return 1
    finally:
        await creator.cleanup_database()
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))