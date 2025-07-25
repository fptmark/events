#!/usr/bin/env python3
"""
Insert bad user records directly into MongoDB for testing validation display
"""
import pymongo
from datetime import datetime, timezone
import time

def insert_bad_users():
    # Connect to MongoDB
    client = pymongo.MongoClient("mongodb://localhost:27017")
    db = client["eventMgr"]
    users_collection = db["user"]
    
    print("🔧 Inserting bad user records for validation testing...")
    
    timestamp = int(time.time())
    bad_users = [
        # Bad gender
        {
            "_id": f"bad_gender_1_{timestamp}",
            "username": f"bad_gender_user_1_{timestamp}",
            "email": f"bad_gender_1_{timestamp}@test.com",
            "password": "password123",
            "firstName": "Bad",
            "lastName": "Gender1",
            "gender": "invalid_gender",  # BAD: not in enum
            "isAccountOwner": True,
            "netWorth": 5000.0,
            "accountId": "507f1f77bcf86cd799439011",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        {
            "_id": f"bad_gender_2_{timestamp}",
            "username": f"bad_gender_user_2_{timestamp}",
            "email": f"bad_gender_2_{timestamp}@test.com",
            "password": "password123",
            "firstName": "Bad",
            "lastName": "Gender2",
            "gender": "attack_helicopter",  # BAD: not in enum
            "isAccountOwner": False,
            "netWorth": 15000.0,
            "accountId": "507f1f77bcf86cd799439011",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        
        # Bad password length
        {
            "_id": f"bad_password_1_{timestamp}",
            "username": f"bad_pwd_user_1_{timestamp}",
            "email": f"bad_pwd_1_{timestamp}@test.com",
            "password": "short",  # BAD: too short (min 8 chars)
            "firstName": "Bad",
            "lastName": "Password1",
            "gender": "male",
            "isAccountOwner": True,
            "netWorth": 8000.0,
            "accountId": "507f1f77bcf86cd799439011",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        {
            "_id": f"bad_password_2_{timestamp}",
            "username": f"bad_pwd_user_2_{timestamp}",
            "email": f"bad_pwd_2_{timestamp}@test.com",
            "password": "x",  # BAD: way too short
            "firstName": "Bad",
            "lastName": "Password2",
            "gender": "female",
            "isAccountOwner": False,
            "netWorth": 12000.0,
            "accountId": "507f1f77bcf86cd799439011",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        
        # Bad accountIds
        {
            "_id": f"bad_account_1_{timestamp}",
            "username": f"bad_account_user_1_{timestamp}",
            "email": f"bad_account_1_{timestamp}@test.com",
            "password": "password123",
            "firstName": "Bad",
            "lastName": "Account1",
            "gender": "male",
            "isAccountOwner": True,
            "netWorth": 3000.0,
            "accountId": "invalid_object_id",  # BAD: not a valid ObjectId
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        {
            "_id": f"bad_account_2_{timestamp}",
            "username": f"bad_account_user_2_{timestamp}",
            "email": f"bad_account_2_{timestamp}@test.com",
            "password": "password123",
            "firstName": "Bad",
            "lastName": "Account2",
            "gender": "other",
            "isAccountOwner": False,
            "netWorth": 7500.0,
            "accountId": "507f1f77bcf86cd799999999",  # BAD: valid format but doesn't exist
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        
        # Bad net worth
        {
            "_id": f"bad_networth_1_{timestamp}",
            "username": f"bad_networth_user_1_{timestamp}",
            "email": f"bad_networth_1_{timestamp}@test.com",
            "password": "password123",
            "firstName": "Bad",
            "lastName": "NetWorth1",
            "gender": "female",
            "isAccountOwner": True,
            "netWorth": -5000.0,  # BAD: negative (min is 0)
            "accountId": "507f1f77bcf86cd799439011",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        {
            "_id": f"bad_networth_2_{timestamp}",
            "username": f"bad_networth_user_2_{timestamp}",
            "email": f"bad_networth_2_{timestamp}@test.com",
            "password": "password123",
            "firstName": "Bad",
            "lastName": "NetWorth2",
            "gender": "male",
            "isAccountOwner": False,
            "netWorth": 15000000.0,  # BAD: too high (max is 10000000)
            "accountId": "507f1f77bcf86cd799439011",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        
        # Bad username (too short)
        {
            "_id": f"bad_username_1_{timestamp}",
            "username": "ab",  # BAD: too short (min 3 chars)
            "email": f"bad_username_1_{timestamp}@test.com",
            "password": "password123",
            "firstName": "Bad",
            "lastName": "Username1",
            "gender": "other",
            "isAccountOwner": True,
            "netWorth": 4000.0,
            "accountId": "507f1f77bcf86cd799439011",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        },
        
        # Bad email format
        {
            "_id": f"bad_email_1_{timestamp}",
            "username": f"bad_email_user_1_{timestamp}",
            "email": "not_an_email",  # BAD: invalid email format
            "password": "password123",
            "firstName": "Bad",
            "lastName": "Email1",
            "gender": "male",
            "isAccountOwner": False,
            "netWorth": 6000.0,
            "accountId": "507f1f77bcf86cd799439011",
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        }
    ]
    
    # Insert all bad records
    result = users_collection.insert_many(bad_users)
    print(f"✅ Inserted {len(result.inserted_ids)} bad user records")
    
    print("\nBad records summary:")
    print("- 2 users with invalid gender values")
    print("- 2 users with passwords too short") 
    print("- 2 users with bad accountId values")
    print("- 2 users with invalid netWorth values")
    print("- 1 user with username too short")
    print("- 1 user with invalid email format")
    
    print(f"\n🔍 You can now test validation display by viewing these users in details/edit modes")
    print(f"   Look for users with timestamps around {timestamp}")
    
    client.close()

if __name__ == "__main__":
    try:
        insert_bad_users()
    except Exception as e:
        print(f"❌ Error: {e}")