package core

import (
	"encoding/json"
	"fmt"
	"strings"

	"validate/pkg/tests"
	"validate/pkg/types"
	"validate/pkg/verifier"
)

// ValidationResult represents the result of test validation
type ValidationResult struct {
	OK     bool
	Issues []string
	Fields map[string][]interface{}
}

// ValidateTest validates a test result and returns validation status
func ValidateTest(testNum int, result *TestResult) *ValidationResult {
	var allIssues []string

	// Check for nil result
	if result == nil {
		return &ValidationResult{
			OK:     false,
			Issues: []string{"Test result is nil"},
			Fields: make(map[string][]interface{}),
		}
	}

	// First do existing verification
	params := verifier.TestParams{
		Sort:   result.Params.Sort,
		Filter: result.Params.Filter,
		Page:   result.Params.Page,
		Size:   result.Params.Size,
		View:   result.Params.View,
	}
	verifyResult := verifier.Verifier.Verify(result.Data, params)
	allIssues = append(allIssues, verifyResult.Issues...)

	// Add pagination validation for collection requests
	paginationIssues := validatePagination(testNum, result)
	allIssues = append(allIssues, paginationIssues...)

	// Add CRUD validation if expected data exists
	crudIssues := validateCRUDResult(testNum, result)
	allIssues = append(allIssues, crudIssues...)

	return &ValidationResult{
		OK:     len(allIssues) == 0,
		Issues: allIssues,
		Fields: verifyResult.Fields,
	}
}

// validatePagination validates pagination data for collection requests
func validatePagination(testNum int, result *TestResult) []string {
	var issues []string

	// Skip pagination validation for non-GET requests
	testCase, err := getTestCaseByID(testNum)
	if err == nil && testCase.Method != "GET" {
		return issues // Only validate pagination for GET requests
	}

	// Check if this is a collection request (no specific ID in URL)
	if !isCollectionRequest(result.URL) {
		return issues // Skip pagination validation for single resource requests
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

// PaginationData represents pagination information from API response
type PaginationData struct {
	Page       int
	PageSize   int
	Total      int
	TotalPages int
}

// extractPagination extracts pagination data from raw JSON response
func extractPagination(rawJSON json.RawMessage) *PaginationData {
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

	return &PaginationData{
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
func validateCRUDResult(testNum int, result *TestResult) []string {
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
func validateErrorResponse(result *TestResult, expectedErrorType string) []string {
	var issues []string

	// Check if response indicates an error
	if result.Status == "200" || result.Status == "201" {
		issues = append(issues, fmt.Sprintf("Expected %s error but got success response", expectedErrorType))
		return issues
	}

	// Validate specific error types based on status and response content
	switch expectedErrorType {
	case "validation":
		if result.Status != "422" && result.Status != "400" {
			issues = append(issues, fmt.Sprintf("Expected validation error (422/400) but got status %s", result.Status))
		}
	case "not_found":
		if result.Status != "404" {
			issues = append(issues, fmt.Sprintf("Expected not found error (404) but got status %s", result.Status))
		}
	case "constraint":
		if result.Status != "409" && result.Status != "422" {
			issues = append(issues, fmt.Sprintf("Expected constraint error (409/422) but got status %s", result.Status))
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
	allTests := tests.GetAllTestCases()
	if testID < 1 || testID > len(allTests) {
		return nil, fmt.Errorf("test ID %d out of range", testID)
	}
	testCase := allTests[testID-1]
	return &testCase, nil
}

