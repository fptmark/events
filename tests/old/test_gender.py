#!/usr/bin/env python3
"""
Quick test script to check gender filtering specifically
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.base_test import BaseTestFramework

class GenderTester(BaseTestFramework):
    """Quick gender filtering test"""
    
    def __init__(self, config_file: str, server_url: str = "http://127.0.0.1:5500", verbose: bool = True):
        super().__init__(config_file, server_url, verbose)
    
    def test_gender_filtering(self):
        """Test gender filtering specifically"""
        print("\n🧪 Testing gender filtering...")
        
        # Test gender=male filtering
        success, response = self.make_api_request("GET", "/api/user?gender=male&pageSize=10")
        if not success:
            print("    ❌ API request failed")
            return False
            
        users = response.get('data', [])
        print(f"    📊 Got {len(users)} users with gender=male filter")
        
        # Check if all returned users have gender=male
        for i, user in enumerate(users):
            user_gender = user.get('gender') 
            print(f"    User {i+1}: id={user.get('id')}, gender={user_gender}")
            
            if user_gender and user_gender != 'male':
                print(f"    ❌ FAIL: Expected gender=male, got gender={user_gender}")
                return False
                
        print(f"    ✅ All {len(users)} users have correct gender=male")
        return True

async def main():
    print("🚀 Starting Gender Filtering Test")
    print("=" * 50)
    
    tester = GenderTester("mongo.json", verbose=True)
    
    # Setup database connection
    if not await tester.setup_database_connection():
        print("❌ Failed to setup database connection")
        return False
    
    try:
        # Test gender filtering
        tester.test("Gender Filtering", tester.test_gender_filtering, True)
        
        # Print summary
        success = tester.summary()
        return success
        
    finally:
        # Always cleanup database connection
        await tester.cleanup_database_connection()

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with exception: {e}")
        sys.exit(1)