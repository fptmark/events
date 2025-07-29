#!/usr/bin/env python3
"""
Simple test script to print the structure of an Account returned from the API
"""
import requests
import json

# API endpoint
base_url = "http://127.0.0.1:5500"

def test_account_api():
    try:
        # GET all accounts
        response = requests.get(f"{base_url}/account/")
        
        if response.status_code == 200:
            accounts = response.json()
            print(f"Successfully retrieved {len(accounts)} accounts")
            
            if accounts:
                # Pretty print the first account
                print("\nAccount structure:")
                print(json.dumps(accounts[0], indent=2))
                
                # Check for specific fields
                print("\nField check:")
                all_fields = accounts[0].keys()
                
                # Base entity fields
                base_fields = ['createdAt', 'updatedAt', '_id']
                for field in base_fields:
                    print(f"Base field '{field}': {'Present' if field in all_fields else 'Missing'}")
                
                # Account-specific fields
                account_fields = ['expiredAt']
                for field in account_fields:
                    print(f"Account field '{field}': {'Present' if field in all_fields else 'Missing'}")
            else:
                print("No accounts found. Try creating one first.")
        else:
            print(f"Error accessing API: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_account_api()