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
        
        print(f"📂 Connecting to {db_type} at {db_uri}/{db_name}")
        await DatabaseFactory.initialize(db_type, db_uri, db_name)
        print("✅ Database connection established")
    
    async def cleanup_database(self):
        """Close database connection"""
        if DatabaseFactory.is_initialized():
            await DatabaseFactory.close()
            print("✅ Database connection closed")
    
    async def create_test_account(self) -> str:
        """Create a test account and return its ID"""
        account_id = str(uuid.uuid4()).replace('-', '')[:24]
        
        account_doc = {
            "id": account_id,
            "name": f"Test Account {account_id[:8]}",
            "type": "business",
            "status": "active",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        }
        
        result, warnings = await DatabaseFactory.save_document("account", account_doc, [])
        if warnings:
            print(f"⚠️ Account creation warnings: {warnings}")
        
        self.test_account_ids.append(account_id)
        print(f"✅ Created test account: {account_id}")
        return account_id
    
    async def create_invalid_user(self, scenario: str, valid_account_id: str) -> str:
        """Create a user with specific validation issues"""
        user_id = str(uuid.uuid4()).replace('-', '')[:24]
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
        
        # Add specific validation issues based on scenario
        if scenario == "bad_enum":
            user_doc["gender"] = "invalid_gender"  # Should be 'male', 'female', or 'other'
            user_doc["netWorth"] = 50000.0  # Valid
            user_doc["accountId"] = valid_account_id  # Valid
            
        elif scenario == "bad_currency":
            user_doc["gender"] = "male"  # Valid
            user_doc["netWorth"] = -5000.0  # Invalid: must be >= 0
            user_doc["accountId"] = valid_account_id  # Valid
            
        elif scenario == "bad_fk":
            user_doc["gender"] = "female"  # Valid
            user_doc["netWorth"] = 75000.0  # Valid
            user_doc["accountId"] = "nonexistent123456789012"  # Invalid: FK doesn't exist
            
        elif scenario == "multiple_errors":
            user_doc["gender"] = "bad_value"  # Invalid enum
            user_doc["netWorth"] = -10000.0  # Invalid currency
            user_doc["accountId"] = "badaccount123456789012"  # Invalid FK
            
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
        
        # 1. Create a valid account for FK references
        valid_account_id = await self.create_test_account()
        
        # 2. Create users with different validation issues
        test_users = {}
        
        scenarios = [
            "bad_enum",      # Invalid gender enum
            "bad_currency",  # Negative netWorth
            "bad_fk",        # Invalid accountId FK
            "multiple_errors" # Multiple validation issues
        ]
        
        for scenario in scenarios:
            user_id = await self.create_invalid_user(scenario, valid_account_id)
            test_users[scenario] = user_id
        
        print(f"\n📊 Test data summary:")
        print(f"   Valid account: {valid_account_id}")
        for scenario, user_id in test_users.items():
            print(f"   User ({scenario}): {user_id}")
        
        return {
            "valid_account_id": valid_account_id,
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
        """Remove ALL test data from database - use with caution!"""
        print("💥 WIPING ALL TEST DATA - This will remove all test users and accounts!")
        
        try:
            # Get all users with test usernames
            all_users, warnings, count = await DatabaseFactory.get_all("user", [])
            deleted_users = 0
            
            for user in all_users:
                username = user.get('username', '')
                email = user.get('email', '')
                # Delete users that look like test data
                if (username.startswith('testuser_') or 
                    email.startswith('test_') or 
                    'test' in username.lower()):
                    user_id = user.get('id')
                    if user_id:
                        try:
                            success = await DatabaseFactory.delete_document("user", user_id)
                            if success:
                                deleted_users += 1
                                print(f"   🗑️ Deleted test user: {username} ({user_id})")
                        except Exception as e:
                            # Ignore delete errors (document may not exist)
                            print(f"   ⚠️ Could not delete user {username}: {e}")
            
            # Get all accounts with test names
            all_accounts, warnings, count = await DatabaseFactory.get_all("account", [])
            deleted_accounts = 0
            
            for account in all_accounts:
                name = account.get('name', '')
                # Delete accounts that look like test data
                if name.startswith('Test Account'):
                    account_id = account.get('id')
                    if account_id:
                        try:
                            success = await DatabaseFactory.delete_document("account", account_id)
                            if success:
                                deleted_accounts += 1
                                print(f"   🗑️ Deleted test account: {name} ({account_id})")
                        except Exception as e:
                            # Ignore delete errors (document may not exist)
                            print(f"   ⚠️ Could not delete account {name}: {e}")
            
            print(f"✅ Database wipe complete: {deleted_users} users, {deleted_accounts} accounts removed")
            
        except Exception as e:
            print(f"❌ Database wipe failed: {e}")
            raise

async def main():
    """Standalone test data creation"""
    import argparse
    parser = argparse.ArgumentParser(description='Test Data Setup')
    parser.add_argument('action', choices=['create', 'cleanup', 'wipe'], 
                       help='Action to perform')
    parser.add_argument('--config', default='mongo.json',
                       help='Config file (default: mongo.json)')
    args = parser.parse_args()
    
    creator = TestDataCreator()
    
    try:
        await creator.setup_database(args.config)
        
        if args.action == 'create':
            test_data = await creator.create_comprehensive_test_data()
            print(f"\n🎯 Test data created successfully!")
            print("Use these IDs in your validation tests:")
            for key, value in test_data.items():
                print(f"  {key}: {value}")
                
        elif args.action == 'cleanup':
            await creator.cleanup_test_data()
            
        elif args.action == 'wipe':
            await creator.wipe_all_test_data()
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        return 1
    finally:
        await creator.cleanup_database()
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))