#!/bin/bash

echo "🧪 Running smoke test for Events API..."
echo "============================================"

# Function to process and analyze API response
process_response() {
    local test_name="$1"
    local url="$2"
    local expected="$3"
    local response="$4"
    
    echo "Test: $test_name"
    echo "URL: $url"
    echo "Expected: $expected"
    echo ""
    
    # Parse response sections
    local data_length=$(echo "$response" | jq '.data | length' 2>/dev/null || echo "0")
    local notifications_length=$(echo "$response" | jq '.notifications | length' 2>/dev/null || echo "0")
    local total=$(echo "$response" | jq '.pagination.total' 2>/dev/null || echo "0")
    local page=$(echo "$response" | jq '.pagination.page' 2>/dev/null || echo "0")
    local per_page=$(echo "$response" | jq '.pagination.per_page' 2>/dev/null || echo "0")
    local total_pages=$(echo "$response" | jq '.pagination.total_pages' 2>/dev/null || echo "0")
    local has_next=$(echo "$response" | jq '.pagination.has_next' 2>/dev/null || echo "false")
    local has_prev=$(echo "$response" | jq '.pagination.has_prev' 2>/dev/null || echo "false")
    
    # Summary section analysis
    local summary_total=$(echo "$response" | jq '.summary.total_entities' 2>/dev/null || echo "0")
    local summary_warnings=$(echo "$response" | jq '.summary.warnings' 2>/dev/null || echo "0")
    local summary_errors=$(echo "$response" | jq '.summary.errors' 2>/dev/null || echo "0")
    
    echo "📊 Response Analysis:"
    echo "  Data section: $data_length entities"
    echo "  Notifications: $notifications_length entities with issues"
    echo "  Summary: $summary_total total, $summary_warnings warnings, $summary_errors errors"
    echo "  Pagination: page $page of $total_pages (per_page: $per_page, total: $total, next: $has_next, prev: $has_prev)"
    echo ""
    
    # Show sample notifications if any exist
    if [ "$notifications_length" != "0" ] && [ "$notifications_length" != "null" ]; then
        echo "🔍 Sample Notifications (first entity):"
        echo "$response" | jq '.notifications | to_entries | .[0].value.warnings[0:2]' 2>/dev/null || echo "  Could not parse sample notifications"
        echo ""
    fi
    
    echo "============================================"
}

# Test 1: API with view parameter should contain data validation, account validation and paging data
echo "Test 1: GET /api/user with view parameter"
results1=$(curl -s "http://localhost:5500/api/user?view=%7b%22account%22%3a%5b%22createdat%22%5d%7d")
process_response \
    "GET /api/user with view parameter" \
    "http://localhost:5500/api/user?view={\"account\":[\"createdAt\"]}" \
    "data validation, account validation, and paging data" \
    "$results1"

# Test 2: API without view parameter should contain data validation, optionally account validation (depending on fk_validation setting) and paging data  
echo "Test 2: GET /api/user without view parameter"
results2=$(curl -s "http://localhost:5500/api/user")
process_response \
    "GET /api/user without view parameter" \
    "http://localhost:5500/api/user" \
    "data validation, optionally account validation (depending on fk_validation setting), and paging data" \
    "$results2"

echo "✅ Smoke test completed"
