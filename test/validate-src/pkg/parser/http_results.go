package parser

import (
	"fmt"

	"validate/pkg/httpclient"
	"validate/pkg/types"
)

var httpExecutor *httpclient.HTTPExecutor

// InitHTTPMode initializes the parser to use HTTP execution instead of file-based parsing
func InitHTTPMode() {
	httpExecutor = httpclient.NewHTTPExecutor()
}

// LoadTestCaseHTTP loads a test case by executing it via HTTP
func LoadTestCaseHTTP(testID int) (*types.TestCase, error) {
	if httpExecutor == nil {
		return nil, fmt.Errorf("HTTP mode not initialized, call InitHTTPMode() first")
	}
	return httpExecutor.LoadTestCase(testID)
}

// CountTestsHTTP returns the number of tests available via HTTP execution
func CountTestsHTTP() (int, error) {
	if httpExecutor == nil {
		return 0, fmt.Errorf("HTTP mode not initialized, call InitHTTPMode() first")
	}
	return httpExecutor.CountTests(), nil
}

// IsHTTPMode returns true if HTTP mode is enabled
func IsHTTPMode() bool {
	return httpExecutor != nil
}

// LoadTestCase loads a test case - HTTP mode only
func LoadTestCase(testID int) (*types.TestCase, error) {
	if !IsHTTPMode() {
		return nil, fmt.Errorf("HTTP mode not initialized")
	}
	return LoadTestCaseHTTP(testID)
}

// CountTests counts tests - HTTP mode only
func CountTests() (int, error) {
	if !IsHTTPMode() {
		return 0, fmt.Errorf("HTTP mode not initialized")
	}
	return CountTestsHTTP()
}