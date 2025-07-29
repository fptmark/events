#!/usr/bin/env python3
"""
Test script to verify Account model inheritance
"""
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.models.account_model import Account, AccountRead, AccountCreate
from app.models.baseentity_model import BaseEntity, BaseEntityRead, BaseEntityBase

class AccountModelTest(unittest.TestCase):
    
    def test_inheritance(self):
        """Test that inheritance is set up correctly"""
        # Print debugging info first
        print("BaseEntityBase annotations:", BaseEntityBase.__annotations__)
        print("BaseEntityRead annotations:", BaseEntityRead.__annotations__)
        print("AccountRead annotations:", AccountRead.__annotations__)
        
        # Document model inheritance
        self.assertTrue(issubclass(Account, BaseEntity))
        
        # Read model inheritance
        self.assertTrue(issubclass(AccountRead, BaseEntityRead))
        
        # Print field information
        print("\nAccount fields:", [f for f in dir(Account) if not f.startswith('_')])
        
        # Print class hierarchy (MRO)
        print("\nAccountRead MRO:", [c.__name__ for c in AccountRead.__mro__])
        
        # Print model_fields (Pydantic v2 way)
        if hasattr(AccountRead, 'model_fields'):
            print("\nAccountRead model_fields:", AccountRead.model_fields.keys())
        if hasattr(BaseEntityRead, 'model_fields'):
            print("BaseEntityRead model_fields:", BaseEntityRead.model_fields.keys())
        
if __name__ == '__main__':
    unittest.main()