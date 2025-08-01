#!/bin/bash

echo "🧪 SMOKE TEST - Basic API Sanity Check"
echo "======================================"

SERVER_URL="http://localhost:5500"
EXIT_CODE=0

# Function to test an endpoint
test_endpoint() {
    local description="$1"
    local url="$2"
    local expected_status="$3"
    
    echo -n "Testing $description... "
    
    response=$(curl -s -w "\n%{http_code}" "$url")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status_code" = "$expected_status" ]; then
        echo "✅ PASS (HTTP $status_code)"
        return 0
    else
        echo "❌ FAIL (HTTP $status_code, expected $expected_status)"
        EXIT_CODE=1
        return 1
    fi
}

# Test 1: Basic API endpoint
test_endpoint "Basic API endpoint" "$SERVER_URL/api/user" "200"

# Test 2: API metadata endpoint
test_endpoint "API metadata" "$SERVER_URL/api/metadata" "200"

# Test 3: Individual user endpoint (404 is acceptable for non-existent user)
echo -n "Testing Individual user endpoint... "
response=$(curl -s -w "\n%{http_code}" "$SERVER_URL/api/user/test_user_123456")
status_code=$(echo "$response" | tail -n1)
if [ "$status_code" = "200" ] || [ "$status_code" = "404" ]; then
    echo "✅ PASS (HTTP $status_code - expected 200 or 404)"
else
    echo "❌ FAIL (HTTP $status_code, expected 200 or 404)"
    EXIT_CODE=1
fi

# Test 4: API with view parameter
test_endpoint "API with view parameter" "$SERVER_URL/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D" "200"

# Test 5: API with pagination
test_endpoint "API with pagination" "$SERVER_URL/api/user?pageSize=5" "200"

echo "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ ALL SMOKE TESTS PASSED - API is responsive"
else
    echo "❌ SOME SMOKE TESTS FAILED - Check API server"
fi

exit $EXIT_CODE