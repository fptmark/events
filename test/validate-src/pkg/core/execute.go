package core

import (
	"encoding/json"

	"validate/pkg/types"
)

// TestResult represents the raw result of executing a test
type TestResult struct {
	ID              int
	URL             string
	Description     string
	TestClass       string
	Data            []map[string]interface{}
	RawResponseBody json.RawMessage // Preserve original JSON order
	Notifications   interface{}
	Status          string
	StatusCode      int
	Params          TestParams
}

// TestParams represents the parameters extracted from the test URL
type TestParams struct {
	Sort   []types.SortField
	Filter map[string][]types.FilterValue
	Page   int
	Size   int
	View   map[string][]string
}

