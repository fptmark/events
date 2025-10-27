"""
Fixture data generation for MCP tests.
Ported from test/validate-src/pkg/tests/fixtures.go

Three-phase data generation:
1. Dynamic pre-data: CreateBulkData() - random test data (acc_r001, usr_r001, etc.)
2. Static data: CreateFixturesFromTestCases() - specific test fixtures
3. Runtime dynamic: Tests create data during execution
"""
import hashlib
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List


# Data arrays for fixture generation
GENDERS = ["male", "female", "other"]

NET_WORTH_VALUES = [
    0, 15000, 25000, 35000, 50000, 75000, 100000, 150000, 250000, 500000,
    750000, 1000000, 2500000, 5000000, 10000000,
]

BIRTH_YEARS = [1950, 1955, 1960, 1965, 1970, 1975, 1980, 1985, 1990, 1995, 2000, 2005]
BIRTH_MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
BIRTH_DAYS = [1, 5, 10, 15, 20, 25, 28]

# Name pools for random data generation
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna",
    "Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle",
    "Kenneth", "Laura", "Kevin", "Sarah", "Brian", "Kimberly", "George", "Deborah",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
]

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "company.com",
    "business.org", "test.net", "example.com", "mail.com", "email.co",
]


def hash_string(s: str) -> int:
    """Return hash value for string (for deterministic array selection)"""
    return int(hashlib.md5(s.encode()).hexdigest(), 16) & 0xFFFFFFFF


async def create_fixture_account(
    mcp_client,
    id: str,
    overrides: Optional[Dict[str, Any]] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Create a test account with given ID and optional field overrides.

    Account schema: expiredAt (Date, optional), createdAt (auto), updatedAt (auto)
    ID convention: acc_{purpose}_{number}
      Examples: acc_valid_001, acc_expired_001, acc_delete_001

    Args:
        mcp_client: MCP client instance
        id: Account ID
        overrides: Optional field overrides
        verbose: Print progress messages

    Returns:
        Created account data
    """
    if verbose:
        print(f"🔧 Creating fixture account: {id}")

    # Use hash of ID to determine if we include optional expiredAt
    hash_val = hash_string(id)

    now = datetime.utcnow().isoformat() + "Z"

    # Build account with required fields
    account = {
        "id": id,
        "createdAt": now,
        "updatedAt": now,
    }

    # Only include expiredAt for some accounts (based on hash)
    if hash_val % 3 == 0:
        # Generate an expired date in the past for some accounts
        days_ago = hash_val % 365
        expired_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        account["expiredAt"] = expired_date

    # Apply overrides
    if overrides:
        account.update(overrides)

    # Create via MCP
    result = await mcp_client.call_tool("create_account", account)

    if verbose:
        print(f"  ✓ Created fixture account: {id}")

    return result


async def create_fixture_user(
    mcp_client,
    id: str,
    account_id: str,
    overrides: Optional[Dict[str, Any]] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Create a test user with given ID, accountId FK, and optional field overrides.

    User schema:
    - Required: username, email, password, firstName, lastName, isAccountOwner, accountId
    - Optional: gender, dob, netWorth, role

    ID convention: usr_{purpose}_{number}
      Examples: usr_basic_001, usr_view_001, usr_delete_001
      For bulk random data: usr_r001, usr_r002, ... usr_rNNN

    Args:
        mcp_client: MCP client instance
        id: User ID
        account_id: Account ID (FK)
        overrides: Optional field overrides
        verbose: Print progress messages

    Returns:
        Created user data
    """
    if verbose:
        print(f"🔧 Creating fixture user: {id}")

    # Use hash of ID to pick deterministic values from arrays
    hash_val = hash_string(id)

    first_name = FIRST_NAMES[hash_val % len(FIRST_NAMES)]
    last_name = LAST_NAMES[(hash_val // 2) % len(LAST_NAMES)]
    domain = EMAIL_DOMAINS[hash_val % len(EMAIL_DOMAINS)]

    username = f"{first_name}_{last_name}_{domain}"
    email = f"{first_name}.{last_name}@{domain}"

    # Generate valid password (min 8 chars from schema)
    password = f"Pass{hash_val % 10000}!"
    if len(password) < 8:
        password = "Password123!"

    now = datetime.utcnow().isoformat() + "Z"

    # Build user with REQUIRED fields only
    user = {
        "id": id,
        "firstName": first_name,
        "lastName": last_name,
        "username": username,
        "email": email,
        "password": password,
        "isAccountOwner": (hash_val % 2 == 0),  # alternate true/false
        "accountId": account_id,
        "createdAt": now,
        "updatedAt": now,
    }

    # OPTIONAL FIELDS - only include sometimes based on hash

    # Include gender ~66% of the time (hash % 3 != 0)
    if hash_val % 3 != 0:
        user["gender"] = GENDERS[hash_val % len(GENDERS)]

    # Include dob ~50% of the time (hash % 2 == 0)
    if hash_val % 2 == 0:
        year = BIRTH_YEARS[hash_val % len(BIRTH_YEARS)]
        month = BIRTH_MONTHS[(hash_val // 3) % len(BIRTH_MONTHS)]
        day = BIRTH_DAYS[(hash_val // 5) % len(BIRTH_DAYS)]
        user["dob"] = f"{year}-{month:02d}-{day:02d}"

    # Include netWorth ~75% of the time (hash % 4 != 0)
    if hash_val % 4 != 0:
        user["netWorth"] = NET_WORTH_VALUES[hash_val % len(NET_WORTH_VALUES)]

    # Apply overrides
    if overrides:
        user.update(overrides)

    # Create via MCP
    result = await mcp_client.call_tool("create_user", user)

    if verbose:
        print(f"  ✓ Created fixture user: {id} (username: {username}, account: {account_id})")

    return result


async def create_bulk_data(
    mcp_client,
    num_accounts: int,
    num_users: int,
    verbose: bool = False
) -> None:
    """
    Create random bulk test accounts and users for get_all testing.

    Phase 1: Dynamic pre-data
    - Accounts: acc_r001, acc_r002, etc.
    - Users: usr_r001, usr_r002, etc. with random varied data

    Args:
        mcp_client: MCP client instance
        num_accounts: Number of accounts to create
        num_users: Number of users to create
        verbose: Print progress messages
    """
    if verbose:
        print("🔧 Creating bulk test data...")

    # Generate random number for domain variability
    y = random.randint(1, num_accounts)

    # Create accounts with ID convention: acc_r001, acc_r002, etc.
    for i in range(1, num_accounts + 1):
        account_id = f"acc_r{i:03d}"
        account = {
            "id": account_id,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "updatedAt": datetime.utcnow().isoformat() + "Z",
        }

        await mcp_client.call_tool("create_account", account)

        if verbose:
            print(f"  ✓ Created account: {account_id}")

    # Create users with ID convention: usr_r001, usr_r002, etc.
    for i in range(1, num_users + 1):
        user_id = f"usr_r{i:03d}"

        # Pick random first and last names
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)

        # Username is <firstname>_<lastname>_xx with round-robin domain
        domain = EMAIL_DOMAINS[(i - 1) % len(EMAIL_DOMAINS)]
        username = f"{first_name}_{last_name}_{domain}"
        email = f"{username}@{domain}"

        # Account ID using round-robin with y component
        account_id = f"acc_r{((i - 1) % y) + 1:03d}"

        # Generate random constrained values
        gender = random.choice(GENDERS)
        net_worth = random.choice(NET_WORTH_VALUES)
        password = f"TestPass{random.randint(100000, 999999)}!"

        user = {
            "id": user_id,
            "firstName": first_name,
            "lastName": last_name,
            "username": username,
            "email": email,
            "accountId": account_id,
            "gender": gender,
            "isAccountOwner": False,
            "netWorth": net_worth,
            "dob": "1990-01-01",
            "password": password,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "updatedAt": datetime.utcnow().isoformat() + "Z",
        }

        await mcp_client.call_tool("create_user", user)

        if verbose:
            print(f"  ✓ Created user: {user_id} (username: {username}, account: {account_id})")

    if verbose:
        print(f"✅ Created {num_accounts} accounts and {num_users} users")


async def create_fixtures_from_test_cases(
    mcp_client,
    test_cases: List[Dict[str, Any]],
    verbose: bool = False
) -> None:
    """
    Create fixtures for all test cases that need pre-existing entities.

    Phase 2: Static data
    - Runs during reset to ensure all fixtures exist before tests run
    - Creates specific test fixtures like usr_get_001, acc_valid_001

    Args:
        mcp_client: MCP client instance
        test_cases: List of test case definitions
        verbose: Print progress messages
    """
    if verbose:
        print("🔧 Creating fixtures from test cases...")

    created_accounts = set()
    created_users = set()

    for test_case in test_cases:
        # Skip create operations - they create entities during test execution
        if test_case.get("operation") in ["create_user", "create_account"]:
            continue

        # Skip if expecting not found - entity shouldn't exist
        if test_case.get("expect_error") == "not_found":
            continue

        # Extract entity type and ID from operation
        operation = test_case.get("operation", "")
        params = test_case.get("params", {})

        # Handle get/update/delete operations that need existing entities
        if operation.startswith("get_") or operation.startswith("update_") or operation.startswith("delete_"):
            entity_id = params.get("id")
            if not entity_id:
                continue

            # Skip entities with nonexist in ID (for error tests)
            if "nonexist" in entity_id:
                continue

            if operation.startswith("get_user") or operation.startswith("update_user") or operation.startswith("delete_user"):
                if entity_id in created_users:
                    continue

                # Get accountId or use default
                account_id = params.get("accountId", "acc_valid_001")

                # Create account if needed
                if "nonexist" not in account_id and account_id not in created_accounts:
                    try:
                        await create_fixture_account(mcp_client, account_id, verbose=verbose)
                        created_accounts.add(account_id)
                    except Exception as e:
                        if verbose:
                            print(f"  ⚠ Account {account_id}: {e}")

                # Create user
                try:
                    await create_fixture_user(mcp_client, entity_id, account_id, params, verbose=verbose)
                    created_users.add(entity_id)
                except Exception as e:
                    if verbose:
                        print(f"  ⚠ User {entity_id}: {e}")

            elif operation.startswith("get_account") or operation.startswith("update_account") or operation.startswith("delete_account"):
                if entity_id in created_accounts:
                    continue

                # Skip accounts with nonexist in ID
                if "nonexist" in entity_id:
                    continue

                # Create account
                try:
                    await create_fixture_account(mcp_client, entity_id, params, verbose=verbose)
                    created_accounts.add(entity_id)
                except Exception as e:
                    if verbose:
                        print(f"  ⚠ Account {entity_id}: {e}")

    # Create special test user for authentication tests
    auth_test_account = "acc_auth_001"
    if auth_test_account not in created_accounts:
        try:
            await create_fixture_account(mcp_client, auth_test_account, verbose=verbose)
            created_accounts.add(auth_test_account)
        except Exception as e:
            if verbose:
                print(f"  ⚠ Account {auth_test_account}: {e}")

    auth_test_user = {
        "username": "mark",
        "password": "12345678",
        "email": "mark@test.com",
        "firstName": "Mark",
        "lastName": "Test",
        "isAccountOwner": True,
    }
    try:
        await create_fixture_user(mcp_client, "usr_auth_001", auth_test_account, auth_test_user, verbose=verbose)
        created_users.add("usr_auth_001")
    except Exception as e:
        if verbose:
            print(f"  ⚠ Auth test user: {e}")

    if verbose:
        print(f"✅ Created {len(created_accounts)} accounts and {len(created_users)} users from test cases")
