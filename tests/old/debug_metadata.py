#!/usr/bin/env python3
import requests
import json

response = requests.get("http://localhost:5500/api/metadata")
if response.status_code == 200:
    data = response.json()
    user_fields = data.get('entities', {}).get('User', {}).get('fields', {})
    
    print("User field validation metadata:")
    for field_name, field_info in user_fields.items():
        print(f"\n{field_name}:")
        for key, value in field_info.items():
            print(f"  {key}: {value}")
else:
    print(f"Error: {response.status_code} - {response.text}")