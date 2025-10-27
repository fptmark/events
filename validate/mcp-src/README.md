# MCP Validator

Comprehensive test framework for the Events API MCP server.

## Overview

The MCP validator tests the MCP (Model Context Protocol) server with the same three-phase data generation pattern as the REST validator:

1. **Dynamic pre-data** - Random bulk test data (acc_r001, usr_r001, etc.)
2. **Static fixtures** - Specific test data for individual test cases
3. **Runtime dynamic** - Data created during test execution

## Architecture

```
test/mcp-validate/
├── mcp_validate/
│   ├── client.py          # MCP client (stdio/JSON-RPC)
│   ├── fixtures.py        # Data generation (ported from Go)
│   ├── test_cases.py      # Test case definitions
│   ├── runner.py          # Test orchestration
│   └── __init__.py
├── validate_mcp.py        # Entry point
├── requirements.txt
└── README.md
```

## Installation

```bash
cd test/mcp-validate
pip install -r requirements.txt
```

## Usage

### Basic Usage

Test with MongoDB backend:
```bash
python validate_mcp.py --config ../../mongo.json
```

Test with SQLite backend:
```bash
python validate_mcp.py --config ../../sqlite.json
```

Test with Elasticsearch backend:
```bash
python validate_mcp.py --config ../../es.json
```

### Options

```bash
python validate_mcp.py [OPTIONS]

Options:
  --server PATH         Path to MCP server script (default: ../../mcp_server.py)
  --config PATH         Path to config file (mongo.json, sqlite.json, es.json)
  --accounts N          Number of random accounts to create (default: 10)
  --users N             Number of random users to create (default: 50)
  --test CLASS          Filter tests by class (basic, create, update, list)
  --verbose, -v         Verbose output
  --no-reset            Skip database reset and population
```

### Examples

**Run all tests verbosely:**
```bash
python validate_mcp.py --config ../../mongo.json --verbose
```

**Run only basic tests:**
```bash
python validate_mcp.py --config ../../sqlite.json --test basic
```

**Run only create tests:**
```bash
python validate_mcp.py --config ../../mongo.json --test create --verbose
```

**Skip reset (use existing data):**
```bash
python validate_mcp.py --config ../../sqlite.json --no-reset
```

**Create more test data:**
```bash
python validate_mcp.py --config ../../mongo.json --accounts 100 --users 500
```

## Test Classes

Tests are organized by type:

- **basic** - Simple get operations (get user, get account, 404 tests)
- **create** - Create operations with validation
- **update** - Update operations
- **list** - List/filter/sort/pagination tests
- **delete** - Delete operations
- **auth** - Authentication tests (future)

## Three-Phase Data Generation

### Phase 1: Dynamic Pre-Data (create_bulk_data)

Creates random test data for list/filter/pagination tests:

**Accounts:**
- IDs: `acc_r001`, `acc_r002`, ... `acc_rNNN`
- Random expiredAt dates based on hash

**Users:**
- IDs: `usr_r001`, `usr_r002`, ... `usr_rNNN`
- Random but deterministic names, emails, genders
- Round-robin assignment to accounts
- Optional fields included probabilistically

### Phase 2: Static Fixtures (create_fixtures_from_test_cases)

Creates specific test data required by individual tests:

**Specific IDs:**
- `usr_get_001`, `usr_get_002` - For GET tests
- `usr_update_001` - For UPDATE tests
- `acc_valid_001`, `acc_valid_002` - Valid accounts for FKs
- `usr_auth_001` - Authentication test user

**Special handling:**
- Skips entities with "nonexist" in ID (for 404 tests)
- Creates accounts before users (FK dependency)
- Uses deterministic but varied data based on ID hash

### Phase 3: Runtime Dynamic

Tests create their own data during execution:

**CREATE tests:**
- Create new users/accounts with test-specific data
- Validate field constraints
- Test required vs optional fields

## Test Case Structure

```python
TestCase(
    name="create_user_all_fields",
    description="Create user with all fields",
    operation="create_user",  # MCP tool name
    params={
        "firstName": "Test",
        "email": "test@example.com",
        # ...
    },
    expect_success=True,
    expected_fields=["id", "firstName", "email"],
    test_class="create"
)
```

## Comparison with REST Validator

| Feature | REST Validator (Go) | MCP Validator (Python) |
|---------|---------------------|------------------------|
| Language | Go | Python |
| Protocol | HTTP REST | stdio/JSON-RPC (MCP) |
| Test data | 3-phase generation | 3-phase generation (same pattern) |
| Fixtures | fixtures.go | fixtures.py (ported) |
| Test cases | static.go | test_cases.py |
| Execution | HTTP client | MCP client |
| Database | MongoDB/ES/SQLite | MongoDB/ES/SQLite (same) |

**Similarities:**
- Same test data generation pattern
- Same fixture IDs and conventions
- Same test scenarios (create, validate, filter, etc.)
- Same database backends

**Differences:**
- Different protocols (HTTP vs stdio)
- Different languages (Go vs Python)
- Different client libraries
- MCP-specific tool invocation

## Output Example

```
============================================================
RESET AND POPULATE
============================================================

🧹 Cleaning database via API...
✅ Database cleaning completed

Phase 1: Creating 10 accounts and 50 users (dynamic pre-data)
  ✓ Created account: acc_r001
  ✓ Created account: acc_r002
  ...
  ✓ Created user: usr_r001
  ✓ Created user: usr_r002
  ...
✅ Created 10 accounts and 50 users

Phase 2: Creating static fixtures from test cases
🔧 Creating fixtures from test cases...
  ✓ Created fixture account: acc_valid_001
  ✓ Created fixture user: usr_get_001
  ...
✅ Created 5 accounts and 12 users from test cases

============================================================
RUNNING TESTS
============================================================

Total tests: 23

[1/23] get_user_valid_001: Get valid user by ID
  ✅ PASS (45.2ms)

[2/23] get_user_valid_002: Get another valid user by ID
  ✅ PASS (38.1ms)

[3/23] get_user_not_found: Get non-existent user
  ✅ PASS (12.5ms)

...

============================================================
TEST SUMMARY
============================================================
Total:  23
Passed: 22 ✅
Failed: 1 ❌

Failed tests:
  • create_user_invalid_gender: Expected validation error but got success
============================================================
```

## Extending Tests

### Add New Test Case

Edit `mcp_validate/test_cases.py`:

```python
TestCase(
    name="my_new_test",
    description="My test description",
    operation="get_user",
    params={"id": "usr_test_001"},
    expect_success=True,
    expected_fields=["id", "username"],
    test_class="basic"
)
```

### Add New Fixture

Edit `mcp_validate/fixtures.py`:

```python
# Add to create_fixtures_from_test_cases()
await create_fixture_user(
    mcp_client,
    "usr_special_001",
    "acc_valid_001",
    {"username": "special", "email": "special@test.com"},
    verbose=verbose
)
```

## Troubleshooting

### MCP Server Won't Start

Check:
1. MCP server path is correct: `--server ../../mcp_server.py`
2. Config file exists: `--config ../../mongo.json`
3. Database is running (MongoDB/Elasticsearch)

### Tests Fail Unexpectedly

Check:
1. Database type matches config (MongoDB vs Elasticsearch vs SQLite)
2. Fresh database reset: remove `--no-reset` flag
3. Server logs for errors

### Connection Issues

Check:
1. MCP server is not already running
2. Port 5500 is available (for REST admin endpoints)
3. Python version >= 3.10

## Development

### Run Tests

```bash
# All tests
python validate_mcp.py --config ../../mongo.json --verbose

# Specific class
python validate_mcp.py --config ../../sqlite.json --test create --verbose
```

### Debug Mode

```bash
# Enable verbose logging
python validate_mcp.py --config ../../mongo.json --verbose
```

### Clean Database Only

```bash
# Clean and populate, but don't run tests
python validate_mcp.py --config ../../mongo.json --verbose
# Then Ctrl+C after population
```

## Future Enhancements

- [ ] Authentication tests
- [ ] Service-specific tests (if MCP exposes services)
- [ ] Performance benchmarks
- [ ] Parallel test execution
- [ ] Test result export (JSON/HTML)
- [ ] Integration with CI/CD
