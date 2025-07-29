# Events Testing Framework

Comprehensive validation and API testing framework for the Events application. Tests model validation, pagination/filtering, API endpoints, and database operations across both MongoDB and Elasticsearch configurations.

## Overview

This testing framework validates:
- **Field Constraints**: netWorth ranges, gender enums, string length limits
- **Database Operations**: Direct insertion bypassing validation
- **API Endpoints**: Create, Read, Update, Delete operations  
- **Pagination & Filtering**: URL parameter parsing, sorting, range filters
- **Validation Logic**: Both write-time and configurable read-time validation
- **Cross-Database**: Works with both MongoDB and Elasticsearch

## Test Suite Structure

### Core Components

1. **Comprehensive Test Runner** (`comprehensive_test.py`)
   - Automated server lifecycle management
   - Multiple database configurations
   - Parallel test execution across configurations
   - Summary reporting with pass/fail statistics

2. **Base Test Framework** (`base_test.py`)
   - Extensible base class for entity testing
   - Database abstraction using DatabaseFactory
   - API testing helpers for HTTP requests
   - Configuration file support (mongo.json, es.json)

3. **Specialized Test Modules**:
   - `test_user_validation.py` - User model validation and CRUD
   - `test_pagination_filtering.py` - Pagination, sorting, filtering APIs
   - `test_server_start_stop.py` - Server lifecycle validation

## Quick Start

```bash
# Run comprehensive test suite (all configurations)
python tests/comprehensive_test.py

# Run comprehensive tests with verbose output
python tests/comprehensive_test.py --verbose

# Run individual test module with specific config
python tests/test_user_validation.py mongo.json --cleanup

# Run pagination tests standalone
python tests/test_pagination_filtering.py

# Run with specific config and verbose mode
python tests/test_user_validation.py es.json --verbose --cleanup
```

## Comprehensive Test Configurations

The comprehensive test runner validates 4 different configurations:

| Configuration | Database | Validation | Description |
|---------------|----------|------------|-------------|
| MongoDB (no validation) | MongoDB | Disabled | Pure storage testing |
| MongoDB (with validation) | MongoDB | Enabled | Full validation testing |
| Elasticsearch (no validation) | Elasticsearch | Disabled | Pure storage testing |
| Elasticsearch (with validation) | Elasticsearch | Enabled | Full validation testing |

Each configuration tests:
- Server startup/shutdown with config
- User model validation scenarios
- Pagination/filtering API endpoints
- Error handling and edge cases

## Test Categories

### 1. Model Validation Tests (`test_user_validation.py`)

**Direct Database Tests**: Verify invalid data can bypass validation:
```python
# Invalid netWorth values (> $10M, negative)
# Invalid gender enums (non-male/female/other)  
# Invalid string fields (too short, bad email format)
```

**API Happy Path Tests**: Valid operations:
```python
# POST /api/user - Create user with currency strings
# GET /api/user - Retrieve all users  
# GET /api/user/{id} - Get specific user
# PUT /api/user/{id} - Update user
```

**API Validation Tests**: Error handling:
```python  
# POST with netWorth > $10M → 422 error
# POST with invalid gender → 422 error
# POST with short username → 422 error
```

**Read-Time Validation**: Configuration-dependent validation:
```python
# Insert invalid data directly to database
# GET requests show warnings when get_validation enabled
```

### 2. Pagination & Filtering Tests (`test_pagination_filtering.py`)

**URL Parameter Parsing**:
- Basic pagination: `?page=2&pageSize=25`
- Sorting: `?sort=name&order=desc`  
- Range filters: `?age=[18:65]&netWorth=[50000:]`
- Text search: `?filter=username:john,email:gmail`
- Complex combinations

**Database Integration**:
- MongoDB aggregation pipeline generation
- Field-type-based matching (text vs exact)
- Sort specification building

**API Endpoint Testing**:
- `/api/user` with various query parameters
- Error handling for invalid parameters
- Response format validation

### 3. Server Lifecycle Tests (`test_server_start_stop.py`)

**Server Management**:
- Clean startup with different configs
- Port availability checking
- Graceful shutdown
- Process cleanup

## URL Testing Examples (with --verbose)

The verbose mode shows actual URLs being tested and their results:

```bash
$ python tests/test_user_validation.py mongo.json --verbose

🔗 Testing URL: GET http://localhost:5500/api/user?page=1&pageSize=25
   ✅ Status: 200 - Retrieved 25 users
   📊 Response time: 145ms

🔗 Testing URL: GET http://localhost:5500/api/user?filter=username:john,age:range:[25:35]
   ✅ Status: 200 - Found 3 matching users
   📊 Response time: 89ms

🔗 Testing URL: POST http://localhost:5500/api/user
   ❌ Status: 422 - Validation failed: netWorth exceeds maximum
   📊 Response time: 52ms
```

### Pagination URL Examples

```bash
# Basic pagination
GET /api/user?page=2&pageSize=15&sort=username&order=asc

# Text search with partial matching  
GET /api/user?filter=username:john,email:gmail

# Enum exact matching
GET /api/user?filter=gender:male,isAccountOwner:true

# Range filtering
GET /api/user?filter=age:range:[21:65],netWorth:range:[25000:100000]

# Complex filtering
GET /api/user?filter=username:smith,age:range:[25:],gender:female&page=3&pageSize=50&sort=createdAt&order=desc
```

## Configuration Files

### mongo.json
```json
{
    "database": "mongodb",
    "db_uri": "mongodb://localhost:27017", 
    "db_name": "eventMgr",
    "get_validation": "get_all",
    "unique_validation": true
}
```

### es.json  
```json
{
    "database": "elasticsearch",
    "db_uri": "http://localhost:9200",
    "db_name": "eventmgr", 
    "get_validation": "get_all",
    "unique_validation": true
}
```

## Command Line Options

### Global Options
- `--verbose` - Show detailed URL testing and response information
- `--cleanup` - Clean up test data after completion
- `--server-url URL` - Use custom server URL (default: http://localhost:5500)

### Test-Specific Options
- `mongo.json` / `es.json` - Use specific database configuration
- `--timeout SECONDS` - Set custom timeout for operations

## Expected Results

### Comprehensive Test Suite
✅ **All Configurations Pass**: 4/4 database configurations working  
✅ **All Test Categories**: Validation, pagination, server lifecycle  
✅ **Performance**: Typical runtime 2-5 minutes for full suite

### Individual Test Modules  
✅ **Direct Database Insertion**: Should succeed (bypasses validation)
✅ **API Happy Path**: Should succeed (valid data passes validation)  
✅ **API Validation Failures**: Should fail with 422 errors (invalid data caught)
✅ **Pagination/Filtering**: Should handle all URL parameter combinations
✅ **GET Validation**: Should show warnings/errors if `get_validation` enabled

## Verbose Mode Output Format

When using `--verbose`, tests show detailed execution information:

```bash
📋 Configuration: MongoDB with validation
🚀 Server: Starting on port 5500
✅ Server: Ready (attempt 3)

🧪 Test Category: User Validation
🔗 URL: GET http://localhost:5500/api/user
   📤 Request: {"headers": {"Content-Type": "application/json"}}
   📥 Response: 200 OK (156ms)
   📊 Data: {"data": [...], "total_count": 42}
   ✅ Result: PASS - Retrieved 42 users

🔗 URL: POST http://localhost:5500/api/user
   📤 Request: {"username": "test", "netWorth": 15000000, ...}  
   📥 Response: 422 Unprocessable Entity (45ms)
   📊 Error: {"detail": [{"field": "netWorth", "message": "exceeds maximum"}]}
   ✅ Result: PASS - Validation correctly rejected invalid data

🛑 Server: Stopped gracefully
📊 Summary: 28/30 tests passed (93.3%)
```

## Extending Tests

### Adding New Entity Tests
1. Create `test_{entity}_validation.py` based on `test_user_validation.py`
2. Inherit from `BaseTestFramework`
3. Implement entity-specific validation scenarios
4. Add to comprehensive test runner

### Adding New URL Scenarios
1. Add test cases to `test_pagination_filtering.py`
2. Include in `TestRealWorldScenarios.test_url_parameter_combinations()`
3. Test with both MongoDB and Elasticsearch

## Troubleshooting

### Server Issues
```
❌ Server failed to start
```
**Solution**: Check database is running, port 5500 is available

### Database Connection
```  
❌ Database connection failed
```
**Solution**: Verify MongoDB/Elasticsearch running and config file correct

### Import Errors
```
❌ No module named 'app'
```
**Solution**: Run from project root: `cd /path/to/events && python tests/...`

### Timeout Issues
```
⏱️ Test timed out after 180s
```
**Solution**: Use `--timeout 300` for slower systems or add `--verbose` to see progress

### No Validation Warnings  
```
⚠️ No validation errors detected in GET
```
**Solution**: Ensure `get_validation: "get_all"` in config and invalid data exists

## Development Workflow

### Running During Development
```bash
# Quick validation test during development
python tests/test_user_validation.py mongo.json --verbose

# Test specific pagination scenarios
python tests/test_pagination_filtering.py --verbose

# Full regression test before commit
python tests/comprehensive_test.py
```

### CI/CD Integration
```bash
# Automated testing (exit code 0 = success, 1 = failure)
python tests/comprehensive_test.py
echo $?  # Check exit code
```

The comprehensive test framework provides confidence that all database configurations, validation rules, pagination features, and API endpoints work correctly across the entire application stack.