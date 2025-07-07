# Events Testing Framework

Comprehensive validation testing framework for the Events application. Tests model validation, API endpoints, and database operations across both MongoDB and Elasticsearch.

## Overview

This testing framework validates:
- **Field Constraints**: netWorth ranges, gender enums, string length limits
- **Database Operations**: Direct insertion bypassing validation
- **API Endpoints**: Create, Read, Update, Delete operations  
- **Validation Logic**: Both write-time and configurable read-time validation
- **Cross-Database**: Works with both MongoDB and Elasticsearch

## Quick Start

```bash
# Ensure server is running
python app/main.py mongo.json

# Run User validation tests with MongoDB
python tests/test_user_validation.py mongo.json --cleanup

# Run User validation tests with Elasticsearch  
python tests/test_user_validation.py es.json --cleanup

# Run tests for both databases
python tests/run_tests.py --all --cleanup
```

## Test Structure

### Base Framework (`base_test.py`)
- **BaseTestFramework**: Extensible base class for entity testing
- **Database Abstraction**: Uses existing DatabaseFactory for cross-database compatibility
- **API Testing**: Helper methods for HTTP requests and validation
- **Configuration**: Command-line config file support (mongo.json, es.json, etc.)

### User Tests (`test_user_validation.py`)
- **Direct Database Tests**: Insert invalid data bypassing model validation
- **API Happy Path**: Valid user creation, retrieval, updates
- **API Validation Failures**: Test constraint enforcement via API
- **GET Validation**: Verify read-time validation works when enabled

## Test Categories

### 1. Direct Database Insertion Tests
Tests that invalid data can be inserted directly into the database (bypassing Pydantic validation):

```python
# Invalid netWorth values (> $10M, negative)
# Invalid gender enums (non-male/female/other)  
# Invalid string fields (too short, bad email format)
```

### 2. API Endpoint Tests - Happy Path
Tests valid operations through the API:

```python
# POST /api/user - Valid user creation with currency strings
# GET /api/user - Retrieve all users
# GET /api/user/{id} - Retrieve specific user
# PUT /api/user/{id} - Update user with valid data
```

### 3. API Endpoint Tests - Validation Failures  
Tests that API validation catches invalid data:

```python
# POST with netWorth > $10,000,000 -> 422 error
# POST with invalid gender enum -> 422 error
# POST with short username/bad email -> 422 error
```

### 4. Read-Time Validation Tests
Tests that GET/GET_ALL validation works when `get_validation: "get_all"` is enabled:

```python
# Insert invalid data directly to database
# GET /api/user should return validation warnings/errors
# Individual GET should also trigger validation
```

## Configuration

The framework uses the same configuration files as the main application:

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

## Usage Examples

### Run Individual Test Suite
```bash
# Test User model with MongoDB
python tests/test_user_validation.py mongo.json

# Test User model with Elasticsearch
python tests/test_user_validation.py es.json

# Test with cleanup
python tests/test_user_validation.py mongo.json --cleanup

# Test with custom server URL
python tests/test_user_validation.py mongo.json --server-url http://localhost:8000
```

### Run Multiple Configurations
```bash
# Test both MongoDB and Elasticsearch
python tests/run_tests.py --all

# Test both with cleanup
python tests/run_tests.py --all --cleanup

# Test specific config
python tests/run_tests.py --config mongo.json --cleanup
```

## Expected Test Results

When running against a properly configured system:

✅ **Direct Database Insertion**: Should succeed (bypasses validation)
✅ **API Happy Path**: Should succeed (valid data passes validation)  
✅ **API Validation Failures**: Should fail with 422 errors (invalid data caught)
✅ **GET Validation**: Should show warnings/errors if `get_validation` enabled

## Extending for Other Entities

To add tests for other entities (Account, Event, etc.):

1. Create `test_{entity}_validation.py` based on `test_user_validation.py`
2. Inherit from `BaseTestFramework`
3. Implement entity-specific validation tests:
   - `test_insert_invalid_{field}_documents()`
   - `test_api_create_{entity}_happy_path()`
   - `test_api_create_{entity}_{field}_validation()`
4. Add entity to `run_tests.py` choices

## Troubleshooting

### Server Not Running
```
❌ Request failed: ConnectionError
```
**Solution**: Start the server first: `python app/main.py mongo.json`

### Database Connection Failed  
```
❌ Database connection failed: ...
```
**Solution**: Ensure MongoDB/Elasticsearch is running and config is correct

### No Validation Errors on GET
```
⚠️ GET validation might be disabled or no invalid data found
```
**Solution**: Check `get_validation: "get_all"` is set in config file

### Import Errors
```
❌ Import error: No module named 'app'
```
**Solution**: Run from project root directory: `cd /path/to/events && python tests/...`