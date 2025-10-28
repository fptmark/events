package tests

import (
	"encoding/json"
	"fmt"
	"strings"

	"validate/pkg/types"
)

// ValidateTest validates a test result and populates Issues and Fields in the TestResult
func ValidateTest(testNum int, result *types.TestResult) {
	// Check for nil result
	if result == nil {
		return
	}

	// Initialize Issues, Notes, and Fields if not already set (dynamic tests may have already populated these)
	if result.Issues == nil {
		result.Issues = []string{}
	}
	if result.Notes == nil {
		result.Notes = []string{}
	}
	if result.Fields == nil {
		result.Fields = make(map[string][]interface{})
	}

	// Check if this is a dynamic test - if so, skip validation (already done internally)
	testCase, err := getTestCaseByID(testNum)
	if err == nil && testCase.TestClass == "dynamic" {
		return // Dynamic tests populate Issues/Fields themselves
	}

	// Extract entity from URL (e.g., "/api/User" -> "User")
	entity := extractEntityFromURL(result.URL)

	// Skip verification for DELETE operations - DELETE ignores query parameters (filter, sort, view)
	// and typically returns empty or minimal data, so validating params against response data doesn't make sense
	if err == nil && testCase.Method != "DELETE" {
		// Perform verification (populates Issues, Notes, and Fields directly in result)
		Verify(result.Data, result.Params, entity, result)
	}

	// Add pagination validation for collection requests
	paginationIssues := validatePagination(testNum, result)
	result.Issues = append(result.Issues, paginationIssues...)

	// Add CRUD validation if expected data exists
	crudIssues := validateCRUDResult(testNum, result)
	result.Issues = append(result.Issues, crudIssues...)
}

// validatePagination validates pagination data for collection requests
func validatePagination(testNum int, result *types.TestResult) []string {
	var issues []string

	// Skip pagination validation for non-GET requests
	testCase, err := getTestCaseByID(testNum)
	if err == nil && testCase.Method != "GET" {
		return issues // Only validate pagination for GET requests
	}

	// Skip pagination validation for dynamic tests (they do their own validation)
	if err == nil && testCase.TestClass == "dynamic" {
		return issues // Dynamic tests handle their own validation
	}

	// Check if this is a collection request (no specific ID in URL)
	if !isCollectionRequest(result.URL) {
		return issues // Skip pagination validation for single resource requests
	}

	// CRITICAL: Collection requests must never return null data
	if hasNullData(result.RawResponseBody) {
		issues = append(issues, "CRITICAL: Collection request returned null data (should be empty array [] instead)")
		return issues
	}

	// Extract pagination data from raw response
	pagination := extractPagination(result.RawResponseBody)
	if pagination == nil {
		issues = append(issues, "Collection request missing pagination data")
		return issues
	}

	// Validate data count matches expected pagination
	expectedCount := min(pagination.PageSize, pagination.Total)
	actualCount := len(result.Data)

	if actualCount != expectedCount {
		issues = append(issues, fmt.Sprintf("Data count mismatch: expected %d records (min(pageSize=%d, total=%d)), got %d",
			expectedCount, pagination.PageSize, pagination.Total, actualCount))
	}

	return issues
}

// isCollectionRequest checks if URL represents a collection request (no specific ID)
func isCollectionRequest(url string) bool {
	// Collection requests don't have specific IDs in the path
	// e.g., "/api/User" vs "/api/User/some_id"
	parts := strings.Split(strings.Trim(url, "/"), "/")
	if len(parts) < 2 {
		return false
	}

	// If URL has more than 2 parts (/api/Entity/id), it's a single resource
	if len(parts) > 2 {
		return false
	}

	return true
}

// extractPagination extracts pagination data from raw JSON response
func extractPagination(rawJSON json.RawMessage) *types.PaginationData {
	var response map[string]interface{}
	if err := json.Unmarshal(rawJSON, &response); err != nil {
		return nil
	}

	paginationObj, exists := response["pagination"]
	if !exists {
		return nil
	}

	pagination, ok := paginationObj.(map[string]interface{})
	if !ok {
		return nil
	}

	// Extract fields with type assertions
	page, ok1 := pagination["page"].(float64)
	pageSize, ok2 := pagination["pageSize"].(float64)
	total, ok3 := pagination["total"].(float64)
	totalPages, ok4 := pagination["totalPages"].(float64)

	if !ok1 || !ok2 || !ok3 || !ok4 {
		return nil
	}

	return &types.PaginationData{
		Page:       int(page),
		PageSize:   int(pageSize),
		Total:      int(total),
		TotalPages: int(totalPages),
	}
}

// min returns the minimum of two integers
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// validateCRUDResult validates CRUD operation results if expected data is specified
func validateCRUDResult(testNum int, result *types.TestResult) []string {
	var issues []string

	// Get the test case to check for expected data
	testCase, err := getTestCaseByID(testNum)
	if err != nil || testCase.ExpectedData == nil {
		return issues // No CRUD validation needed
	}

	expected := testCase.ExpectedData

	// If expecting an error type, validate the error response
	if expected.ExpectedErrorType != "" {
		return validateErrorResponse(result, expected.ExpectedErrorType)
	}

	// For successful operations, validate the response data
	if len(result.Data) == 0 {
		issues = append(issues, "CRUD operation should return data but got empty response")
		return issues
	}

	// Validate first record (for POST/PUT operations)
	record := result.Data[0]

	// Check required fields are present
	for _, field := range expected.ShouldContainFields {
		if _, exists := record[field]; !exists {
			issues = append(issues, fmt.Sprintf("CRUD result missing required field: %s", field))
		}
	}

	// Check prohibited fields are not present
	for _, field := range expected.ShouldNotContainFields {
		if _, exists := record[field]; exists {
			issues = append(issues, fmt.Sprintf("CRUD result contains prohibited field: %s", field))
		}
	}

	// Check specific field values match expectations
	for fieldName, expectedValue := range expected.ExpectedFields {
		if actualValue, exists := record[fieldName]; !exists {
			issues = append(issues, fmt.Sprintf("CRUD result missing expected field: %s", fieldName))
		} else if !valuesEqual(actualValue, expectedValue) {
			issues = append(issues, fmt.Sprintf("CRUD field %s: expected %v, got %v", fieldName, expectedValue, actualValue))
		}
	}

	return issues
}

// validateErrorResponse validates that the response indicates the expected error type
func validateErrorResponse(result *types.TestResult, expectedErrorType string) []string {
	var issues []string

	// Check if response indicates an error
	if result.StatusCode == 200 || result.StatusCode == 201 {
		issues = append(issues, fmt.Sprintf("Expected %s error but got success response", expectedErrorType))
		return issues
	}

	// Validate specific error types based on status and response content
	switch expectedErrorType {
	case "validation":
		if result.StatusCode != 422 && result.StatusCode != 400 {
			issues = append(issues, fmt.Sprintf("Expected validation error (422/400) but got status %d", result.StatusCode))
		}
	case "not_found":
		if result.StatusCode != 404 {
			issues = append(issues, fmt.Sprintf("Expected not found error (404) but got status %d", result.StatusCode))
		}
	case "constraint":
		if result.StatusCode != 409 && result.StatusCode != 422 {
			issues = append(issues, fmt.Sprintf("Expected constraint error (409/422) but got status %d", result.StatusCode))
		}
	}

	return issues
}

// valuesEqual compares two values for equality, handling type conversions
func valuesEqual(actual, expected interface{}) bool {
	// Handle numeric comparisons
	if actualFloat, ok := actual.(float64); ok {
		if expectedFloat, ok := expected.(float64); ok {
			return actualFloat == expectedFloat
		}
		if expectedInt, ok := expected.(int); ok {
			return actualFloat == float64(expectedInt)
		}
	}

	// Handle string comparisons
	if actualStr, ok := actual.(string); ok {
		if expectedStr, ok := expected.(string); ok {
			return actualStr == expectedStr
		}
	}

	// Handle boolean comparisons
	if actualBool, ok := actual.(bool); ok {
		if expectedBool, ok := expected.(bool); ok {
			return actualBool == expectedBool
		}
	}

	// Fallback to direct comparison
	return actual == expected
}

// getTestCaseByID retrieves a test case by its ID (helper function)
func getTestCaseByID(testID int) (*types.TestCase, error) {
	allTests := GetAllTestCases()
	if testID < 1 || testID > len(allTests) {
		return nil, fmt.Errorf("test ID %d out of range", testID)
	}
	testCase := allTests[testID-1]
	return &testCase, nil
}

// extractEntityFromURL extracts the entity type from a URL
// Examples: "/api/User" -> "User", "/api/User/usr_001" -> "User", "/api/Account?filter=..." -> "Account"
func extractEntityFromURL(url string) string {
	// Remove query params
	if idx := strings.Index(url, "?"); idx != -1 {
		url = url[:idx]
	}

	// Split by / and get the entity part
	parts := strings.Split(strings.Trim(url, "/"), "/")
	if len(parts) >= 2 {
		return parts[1] // "api/User" -> "User"
	}

	return "User" // Default fallback
}

// hasNullData checks if the response contains "data": null
func hasNullData(rawJSON json.RawMessage) bool {
	var response map[string]interface{}
	if err := json.Unmarshal(rawJSON, &response); err != nil {
		return false
	}

	dataVal, exists := response["data"]
	if !exists {
		return false
	}

	// Check if data is explicitly null
	return dataVal == nil
}
