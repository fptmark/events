package types

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

// TestCase represents a single test case
type TestCase struct {
	ID          int        `json:"id"`
	URL         string     `json:"url"`
	Method      string     `json:"method"`
	Description string     `json:"description"`
	Status      int        `json:"status"`      // HTTP status code
	Params      TestParams `json:"params"`
	Result      TestResult `json:"result"`
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