package tests

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	"validate/pkg/core"
	"validate/pkg/tests/dynamic"
	"validate/pkg/types"
)

// HTTPExecutor executes API tests in real-time
type HTTPExecutor struct {
	client *http.Client
}

// NewHTTPExecutor creates a new HTTP executor
func NewHTTPExecutor() *HTTPExecutor {
	return &HTTPExecutor{
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// ExecuteTest is a package-level function that executes a test using the default executor
func ExecuteTest(testNumber int) (*types.TestResult, error) {
	executor := NewHTTPExecutor()
	return executor.ExecuteTest(testNumber)
}

// ExecuteTest executes a test by number and returns TestResult
func (e *HTTPExecutor) ExecuteTest(testNumber int) (*types.TestResult, error) {
	// Get test definition from static test suite
	allTests := GetAllTestCases()
	testCase := allTests[testNumber-1] // testNumber is 1-based

	// Handle dynamic tests (includes "dynamic" and "authz" test classes)
	if testCase.TestClass == "dynamic" || testCase.TestClass == "authz" {
		function_if := dynamic.GetDynamicTest(testCase.URL)
		if function_if == nil {
			fmt.Fprintf(os.Stderr, "no dynamic function found for URL: %s\n", testCase.URL)
			os.Exit(1)
		}
		result, err := function_if()
		return result, err
	}

	// Execute the test
	result, err := e.executeTestCase(&testCase)
	if err != nil {
		return nil, err
	}

	// Set the test number and URL
	result.TestNum = testNumber
	result.URL = testCase.URL

	return result, nil
}

// executeTestCase executes a single test case and returns a TestResult
func (e *HTTPExecutor) executeTestCase(testCase *types.TestCase) (*types.TestResult, error) {
	// Build full URL using GlobalConfig.ServerURL
	fullURL := core.ServerURL + testCase.URL

	// Use the ExecuteURL function to perform the HTTP request
	resp, responseBody, err := core.ExecuteURL(fullURL, testCase.Method, testCase.RequestBody)
	if err != nil {
		return nil, err
	}

	// Parse response to TestResult format
	result, err := parseHTTPResponse(resp, responseBody, testCase.URL)
	if err != nil {
		return nil, err
	}

	// Parse URL parameters from the full URL
	params, err := ParseTestURL(fullURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL parameters: %w", err)
	}
	result.Params = *params

	return result, nil
}

// parseHTTPResponse converts raw HTTP response to TestResult format
func parseHTTPResponse(resp *http.Response, responseBody []byte, url string) (*types.TestResult, error) {
	// Parse the response body as JSON
	var responseData interface{}
	if err := json.Unmarshal(responseBody, &responseData); err != nil {
		// If JSON parsing fails, treat as error response
		responseData = string(responseBody)
	}

	// Create base result
	result := &types.TestResult{
		TestNum:         0, // Will be set by caller if needed
		StatusCode:      resp.StatusCode,
		RawResponseBody: json.RawMessage(responseBody),
		Data:            []map[string]interface{}{},
	}

	// Handle different response types
	if responseMap, ok := responseData.(map[string]interface{}); ok {
		// Standard API response format
		if dataVal, exists := responseMap["data"]; exists {
			switch d := dataVal.(type) {
			case []interface{}:
				for _, item := range d {
					if itemMap, ok := item.(map[string]interface{}); ok {
						result.Data = append(result.Data, itemMap)
					}
				}
			case map[string]interface{}:
				result.Data = append(result.Data, d)
			case nil:
				result.Data = []map[string]interface{}{}
			}
		}

		// Extract notifications
		if notifVal, exists := responseMap["notifications"]; exists {
			result.Notifications = notifVal
		}
	} else {
		// Non-standard response (error, plain text, etc.)
		result.Data = []map[string]interface{}{}
		result.Notifications = nil
	}

	return result, nil
}

// ExecuteTests runs all tests and returns results
func ExecuteTests(testNumbers []int) ([]*types.TestResult, error) {
	allTestCases := GetAllTestCases()
	totalTests := len(allTestCases)

	// Validate all test numbers first
	for _, testNum := range testNumbers {
		if testNum < 1 || testNum > totalTests {
			return nil, fmt.Errorf("test number %d out of range (1-%d)", testNum, totalTests)
		}
	}

	results := make([]*types.TestResult, len(testNumbers))

	lastUpdate := time.Now()
	showing_progress := false

	for i, testNum := range testNumbers {
		// Show progress update if more than 1 second since last update
		now := time.Now()
		if now.Sub(lastUpdate) > 1*time.Second {
			fmt.Fprintf(os.Stderr, "\rRunning test %d  ", testNum)
			lastUpdate = now
			showing_progress = true
		}

		// Execute test
		result, err := ExecuteTest(testNum)
		results[i] = result

		if err != nil || result == nil {
			continue
		}

		testCase := allTestCases[testNum-1]

		if result.StatusCode >= 400 {
			// Special case: CREATE test expecting 201 but got 409 (already exists)
			if testCase.Method == "POST" && testCase.ExpectedStatus == 201 && result.StatusCode == 409 {
				result.Alert = true
				result.Passed = false
			} else {
				result.Passed = result.StatusCode == testCase.ExpectedStatus
			}
			continue
		}

		// Count warnings, request warnings, and errors in notifications
		if result.Notifications != nil {
			if notifMap, ok := result.Notifications.(map[string]interface{}); ok {
				if warningsMap, ok := notifMap["warnings"].(map[string]interface{}); ok {
					for _, entityWarnings := range warningsMap {
						if entityMap, ok := entityWarnings.(map[string]interface{}); ok {
							for _, entityErrors := range entityMap {
								if errorsList, ok := entityErrors.([]interface{}); ok {
									for _, errorItem := range errorsList {
										if errorMap, ok := errorItem.(map[string]interface{}); ok {
											if errorType, ok := errorMap["type"].(string); ok {
												switch errorType {
												case "warning":
													result.Warnings++
												case "request_warning":
													result.RequestWarnings++
												case "error":
													result.Errors++
												}
											}
										}
									}
								}
							}
						}
					}
				}
			}
		}

		// Populate validation issues and fields (modifies result in place)
		ValidateTest(testNum, result)

		// Determine pass/fail
		statusMatch := result.StatusCode == testCase.ExpectedStatus
		noValidationIssues := len(result.Issues) == 0

		// Store pass/fail in result
		result.Passed = statusMatch && noValidationIssues && result.Errors == 0
	}

	// Clear the progress line if it was shown
	if showing_progress {
		fmt.Fprintf(os.Stderr, "\r%s\r", strings.Repeat(" ", 50))
	}

	return results, nil
}
