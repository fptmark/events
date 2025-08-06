import random
import string
import uuid
from datetime import datetime, timedelta

from typing import Dict, Any, List, Tuple

import json5

class RandomData():

    def __init__(self, metadata: str, entity: str = "user"):
        all_metadata = json5.loads(metadata)
        if isinstance(all_metadata, dict):
            entities = all_metadata.get('entities', {})
            if isinstance(entities, dict):
                self.metadata = entities.get(entity.capitalize(), {})
            else:
                self.metadata = {}
        
        self.entity = entity.lower()

    def generate_records(self, good_count=50, bad_count=20, include_known_test_records=True) -> Tuple[List, List]:
        """Generate a mix of valid and invalid records based on field metadata."""
        valid_records = []
        invalid_records = []

        # Create specific known test records first (if requested)
        if include_known_test_records:
            known_valid, known_invalid = self._load_fixed_records()
            valid_records.extend(known_valid)
            invalid_records.extend(known_invalid)

        # Generate additional random valid records
        for i in range(good_count):
            record = {}
            for field, meta in self.metadata.get('fields', {}).items():
                record[field] = self.generate_valid_value(field, meta)
            record["id"] = f"generated_valid_{i+1}"
            valid_records.append(record)

        # Generate additional random invalid records
        for i in range(bad_count):
            record = {}
            for field, meta in self.metadata.get('fields', {}).items():
                record[field] = self.generate_invalid_value(field, meta)
            record["id"] = f"generated_invalid_{i+1}"
            invalid_records.append(record)

        return valid_records, invalid_records
    
    def _load_fixed_records(self) -> Tuple[List, List]:
        """Load specific known test records using dynamic import based on entity."""
        try:
            # Dynamic import based on entity name
            module_name = f"fixed_{self.entity}s"  # e.g., "fixed_users", "fixed_accounts"
            class_name = f"Fixed{self.entity.capitalize()}s"  # e.g., "FixedUsers", "FixedAccounts"
            
            # Import the module dynamically
            import importlib
            try:
                module = importlib.import_module(f"tests.{module_name}")
                fixed_class = getattr(module, class_name)
                return fixed_class.create_known_test_records()
            except (ImportError, AttributeError) as e:
                print(f"⚠️ Warning: Could not load fixed records for {self.entity}: {e}")
                print(f"  Expected: tests/{module_name}.py with class {class_name}")
                print(f"  Falling back to random records only")
                return [], []
                
        except Exception as e:
            print(f"⚠️ Warning: Error loading fixed records: {e}")
            return [], []

    def rand_string(self, min_len, max_len):
        # Ensure valid range for randint
        actual_max = min(max_len, 200)  # Increased limit for testing purposes
        if min_len > actual_max:
            actual_max = min_len  # Ensure min <= max
        return ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(min_len, actual_max)))

    def rand_email(self, min_len, max_len):
        while True:
            email = self.rand_string(3, 10) + "@" + self.rand_string(3, 5) + ".com"
            if min_len <= len(email) <= max_len:
                return email

    def rand_url(self, min_len, max_len, count=0):
        if min_len < 22 or max_len > 100:
            print("URL length constraints are too strict")
            raise ValueError("Invalid URL length constraints")
        while True:
            url = "http://www." + self.rand_string(3, 10) + "." + self.rand_string(3, 5) + ".com"
            if len(url) < min_len or len(url) > max_len:
               return self.rand_url(min_len, max_len, count + 1) if count < 10 else None
            return url

    def rand_date(self, ):
        return (datetime.now() - timedelta(days=random.randint(1000, 25000))).date().isoformat()

    def rand_datetime(self, ):
        return datetime.now().isoformat()

    def generate_valid_value(self, field, meta):
        if "enum" in meta:
            values = meta["enum"]["values"] if isinstance(meta["enum"], dict) else meta["enum"]
            return random.choice(values)
        t = meta.get("type")
        if t == "String":
            min_len = meta.get("min_length", 1)
            max_len = min(meta.get("max_length", 100), 100)
            if field == "email":
                return self.rand_email(min_len, max_len)
            if field == "url":
                return self.rand_url(min_len, max_len)
            return self.rand_string(min_len, max_len)
        if t == "Boolean":
            return random.choice([True, False])
        if t == "Date":
            return self.rand_date()
        if t == "Datetime":
            return self.rand_datetime()
        if t == "Currency":
            return round(random.uniform(meta.get("ge", 0), meta.get("le", 1e6)), 2)
        if t == "ObjectId":
            return uuid.uuid4().hex[:24]
        return None

    def generate_invalid_value(self, field, meta):
        t = meta.get("type")
        if "enum" in meta:
            return "invalid_enum"
        if t == "String":
            min_len = meta.get("min_length", 0)
            max_len = meta.get("max_length", 100)
            
            if random.random() < 0.5 and min_len > 0:
                if min_len <= 1:
                    return ""
                # Generate string that's too short (but at least length 0)
                too_short_len = max(1, min_len - 1)
                return self.rand_string(1, too_short_len)  # 1 to (min_len-1)
            else:
                # Generate string that's too long
                return self.rand_string(max_len + 1, max_len + 10)
        if t == "Boolean":
            return "not_a_boolean"
        if t == "Date":
            # ES is stricter about invalid dates - use a real but incorrect date format
            return "2023-99-99"  # Invalid month/day but parseable
        if t == "Datetime":
            # ES is stricter about invalid dates - use a real but incorrect datetime format  
            return "2023-99-99T25:61:61Z"  # Invalid month/day/time but parseable
        if t == "Currency":
            return meta.get("le", 1e6) + random.randint(1, 10000)
        if t == "ObjectId":
            return "short"
        return None


    # Output to inspect
    # print("VALID RECORDS (sample):", valid_records[:2])
    # print("INVALID RECORDS (sample):", invalid_records[:2])
