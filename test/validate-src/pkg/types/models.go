package types

import (
	"encoding/json"
)

// TestResult represents the JSON response from an API test
type TestResult struct {
	Data          []map[string]interface{} `json:"data"`
	Notifications interface{}              `json:"notifications"` // Keep raw structure for complex nested warnings
	Status        string                   `json:"status"`
}

// Notification represents a notification in the API response
type Notification struct {
	Type    string                 `json:"type"`
	Message string                 `json:"message"`
	Details map[string]interface{} `json:"details,omitempty"`
}

// TestParams represents parsed URL parameters from a test
type TestParams struct {
	Sort   []SortField            `json:"sort"`
	Filter map[string][]FilterValue `json:"filter"`
	View   map[string][]string    `json:"view"`
	Page   int                    `json:"page"`
	PageSize int                  `json:"pageSize"`
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

// TestCase represents a single test case with both static definition and runtime execution data
type TestCase struct {
	ID             int                    `json:"id"`
	URL            string                 `json:"url"`             // Relative URL path (e.g., "/api/User")
	Method         string                 `json:"method"`          // HTTP method (GET, POST, PUT, DELETE)
	Description    string                 `json:"description"`
	TestClass      string                 `json:"test_class"`      // Test category (basic, view, sort, etc.)
	ExpectedStatus int                    `json:"expected_status"` // Expected HTTP status code
	RequestBody    map[string]interface{} `json:"request_body,omitempty"` // Request payload for POST/PUT/DELETE
	ExpectedData   *CRUDExpectation       `json:"expected_data,omitempty"` // Expected result data for CRUD operations

	// Runtime execution data (populated during test execution)
	ActualStatus    int             `json:"actual_status,omitempty"`    // Actual HTTP response status
	RawResponseBody json.RawMessage `json:"raw_response_body,omitempty"` // Original HTTP response body preserving field order
	Params          TestParams      `json:"params,omitempty"`           // Parsed URL parameters
	Result          TestResult      `json:"result,omitempty"`           // API response data
}

// VerificationResult represents the outcome of verification
type VerificationResult struct {
	TestID      int                    `json:"test_id"`
	URL         string                 `json:"url"`
	Description string                 `json:"description"`
	Fields      map[string]interface{} `json:"fields"`
	Passed      bool                   `json:"passed"`
	Issues      []string               `json:"issues,omitempty"`
}

// FieldExtraction represents extracted field data for verification
type FieldExtraction struct {
	SortFields   map[string][]interface{} `json:"sort_fields"`
	FilterFields map[string][]interface{} `json:"filter_fields"`
	ViewFields   map[string][]interface{} `json:"view_fields"`
}

// CRUDExpectation represents expected data for CRUD operation validation
type CRUDExpectation struct {
	// For POST: expected fields in created record
	// For PUT: expected fields after update
	// For DELETE: nil (just check success)
	ExpectedFields map[string]interface{} `json:"expected_fields,omitempty"`

	// For validation of specific response patterns
	ShouldContainFields []string `json:"should_contain_fields,omitempty"` // Fields that must be present
	ShouldNotContainFields []string `json:"should_not_contain_fields,omitempty"` // Fields that must not be present

	// For error validation
	ExpectedErrorType string `json:"expected_error_type,omitempty"` // "validation", "not_found", "constraint", etc.
}