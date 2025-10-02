package core

import (
	"encoding/json"
	"fmt"
	"strings"

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
	paginationIssues := validatePagination(result)
	allIssues = append(allIssues, paginationIssues...)

	return &ValidationResult{
		OK:     len(allIssues) == 0,
		Issues: allIssues,
		Fields: verifyResult.Fields,
	}
}

// validatePagination validates pagination data for collection requests
func validatePagination(result *TestResult) []string {
	var issues []string

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