#!/usr/bin/env python3
"""
Test script to check if models are working correctly
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent))

from app.models.account_model import Account, AccountRead, AccountCreate
from app.models.baseentity_model import BaseEntity
from datetime import datetime
import json

# Test creating an account
account = Account(expiredAt=None)
print(f"Account created: {account}")
print(f"Account has BaseEntity fields: createdAt={account.createdAt}, updatedAt={account.updatedAt}")

# Test serialization
account_dict = account.dict()
print(f"Account serialized to dict: {json.dumps(account_dict, default=str, indent=2)}")

# Test read model
account_read = AccountRead(
    _id="507f1f77bcf86cd799439011",
    createdAt=datetime.utcnow(),
    updatedAt=datetime.utcnow(),
    expiredAt=None
)
print(f"AccountRead model: {account_read}")
print(f"AccountRead serialized: {json.dumps(account_read.dict(by_alias=True), default=str, indent=2)}")