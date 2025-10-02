package core

import (
	"encoding/json"

	"validate/pkg/parser"
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

// RunTest executes a single test and returns raw result data
func RunTest(testNum int) (*TestResult, error) {
	// Load and execute the test using existing parser
	testCase, err := parser.LoadTestCase(testNum)
	if err != nil {
		return nil, err
	}

	// Convert to clean result format
	result := &TestResult{
		ID:              testCase.ID,
		URL:             testCase.URL,
		Description:     testCase.Description,
		TestClass:       testCase.TestClass,
		Data:            testCase.Result.Data,
		RawResponseBody: testCase.RawResponseBody,
		Notifications:   testCase.Result.Notifications,
		Status:          testCase.Result.Status,
		StatusCode:      testCase.ActualStatus,
		Params: TestParams{
			Sort:   testCase.Params.Sort,
			Filter: testCase.Params.Filter,
			Page:   testCase.Params.Page,
			Size:   testCase.Params.PageSize,
			View:   testCase.Params.View,
		},
	}

	return result, nil
}