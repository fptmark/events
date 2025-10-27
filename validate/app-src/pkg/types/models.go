package types

import (
	"encoding/json"
)

// TestResult represents the result of executing a test
type TestResult struct {
	TestNum         int    // Test number (1-based) - use to look up TestCase
	URL             string // URL for this test (needed for validation)
	Data            []map[string]interface{}
	RawResponseBody json.RawMessage
	Notifications   interface{}
	StatusCode      int
	Params          TestParams
	Passed          bool // Overall pass/fail determined by ExecuteTests
	Alert           bool // True if CREATE test got 409 (record already exists)
	Warnings        int  // Count of warnings in notifications
	RequestWarnings int  // Count of request warnings in notifications
	Errors          int  // Count of errors in notifications

	// Validation fields (populated by ValidateTest for static tests, or directly by dynamic tests)
	Issues []string                 // Validation issues found
	Notes  []string                 // Informational notes (not errors)
	Fields map[string][]interface{} // Field values extracted during validation
}

// TestParams represents parsed URL parameters from a test
type TestParams struct {
	Sort        []SortField              `json:"sort"`
	Filter      map[string][]FilterValue `json:"filter"`
	FilterMatch string                   `json:"filter_match"` // "substring" (default) or "full"
	View        map[string][]string      `json:"view"`
	Page        int                      `json:"page"`
	PageSize    int                      `json:"pageSize"`
}

// SortField represents a sort parameter field:direction
type SortField struct {
	Field     string `json:"field"`
	Direction string `json:"direction"` // "asc" or "desc"
}

// FilterValue represents a filter parameter value
type FilterValue struct {
	Operator string      `json:"operator"` // "eq", "gt", "gte", "lt", "lte"
	Value    interface{} `json:"value"`
}

// TestCase represents a single test case static definition
type TestCase struct {
	ID             int                    `json:"id"`
	URL            string                 `json:"url"`    // Relative URL path (e.g., "/api/User")
	Method         string                 `json:"method"` // HTTP method (GET, POST, PUT, DELETE)
	Description    string                 `json:"description"`
	TestClass      string                 `json:"test_class"`              // Test category (basic, view, sort, etc.)
	ExpectedStatus int                    `json:"expected_status"`         // Expected HTTP status code
	RequestBody    map[string]interface{} `json:"request_body,omitempty"`  // Request payload for POST/PUT/DELETE
	ExpectedData   *CRUDExpectation       `json:"expected_data,omitempty"` // Expected result data for CRUD operations
}

// CRUDExpectation represents expected data for CRUD operation validation
type CRUDExpectation struct {
	// For POST: expected fields in created record
	// For PUT: expected fields after update
	// For DELETE: nil (just check success)
	ExpectedFields map[string]interface{} `json:"expected_fields,omitempty"`

	// For validation of specific response patterns
	ShouldContainFields    []string `json:"should_contain_fields,omitempty"`     // Fields that must be present
	ShouldNotContainFields []string `json:"should_not_contain_fields,omitempty"` // Fields that must not be present

	// For error validation
	ExpectedErrorType string `json:"expected_error_type,omitempty"` // "validation", "not_found", "constraint", etc.
}

// PaginationData represents pagination information from API response
type PaginationData struct {
	Page       int
	PageSize   int
	Total      int
	TotalPages int
}

// CategoryStats represents test result statistics for a category
type CategoryStats struct {
	Success int
	Failed  int
}
