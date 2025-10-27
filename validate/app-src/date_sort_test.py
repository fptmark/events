#!/usr/bin/env python3

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_date_sorting_with_collation():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.eventMgr
    collection = db.User

    # Test the exact sort specification that should be used
    sort_spec = [('isAccountOwner', 1), ('dob', -1), ('firstName', 1)]

    # Test different approaches to make dob:desc work
    test_cases = [
        {"name": "Standard sort spec", "sort": [('isAccountOwner', 1), ('dob', -1), ('firstName', 1)], "collation": None},
        {"name": "String field for dob", "sort": [('isAccountOwner', 1), ('dob', -1), ('firstName', 1)], "collation": None, "string_dob": True},
        {"name": "Only dob desc", "sort": [('dob', -1)], "collation": None},
        {"name": "No collation multi", "sort": [('isAccountOwner', 1), ('dob', -1), ('firstName', 1)], "collation": None},
        {"name": "Skip collation on date fields", "sort": [('isAccountOwner', 1), ('dob', -1), ('firstName', 1)], "collation": {"locale": "simple", "strength": 1}, "skip_collation": True},
    ]

    for test_case in test_cases:
        print(f"\n=== {test_case['name']} ===")

        cursor = collection.find({}).sort(test_case["sort"]).limit(25)

        # Apply collation unless we're testing skipping it
        if test_case.get("collation") and not test_case.get("skip_collation"):
            cursor = cursor.collation(test_case["collation"])

        docs = await cursor.to_list(length=25)

        # Show isAccountOwner and dob for first few and last few records
        print("First 3 records:")
        for i in range(min(3, len(docs))):
            doc = docs[i]
            dob_str = doc['dob'].strftime('%Y-%m-%d') if hasattr(doc['dob'], 'strftime') else str(doc['dob'])
            print(f"  {doc['isAccountOwner']} | {dob_str} | {doc['firstName']}")

        if len(docs) > 6:
            print("...")
            print("Last 3 records:")
            for i in range(max(0, len(docs)-3), len(docs)):
                doc = docs[i]
                dob_str = doc['dob'].strftime('%Y-%m-%d') if hasattr(doc['dob'], 'strftime') else str(doc['dob'])
                print(f"  {doc['isAccountOwner']} | {dob_str} | {doc['firstName']}")

        # Check the transition point between false and true isAccountOwner
        transition_found = False
        for i in range(len(docs)-1):
            if docs[i]['isAccountOwner'] != docs[i+1]['isAccountOwner']:
                print(f"Transition at index {i}->{i+1}:")
                for j in range(max(0, i-1), min(len(docs), i+3)):
                    doc = docs[j]
                    dob_str = doc['dob'].strftime('%Y-%m-%d') if hasattr(doc['dob'], 'strftime') else str(doc['dob'])
                    marker = " <-- TRANSITION" if j == i or j == i+1 else ""
                    print(f"  [{j}] {doc['isAccountOwner']} | {dob_str} | {doc['firstName']}{marker}")
                transition_found = True
                break

        if not transition_found:
            print("No transition found (all same isAccountOwner value)")

if __name__ == "__main__":
    asyncio.run(test_date_sorting_with_collation())