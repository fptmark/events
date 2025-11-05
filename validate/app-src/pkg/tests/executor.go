package tests

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"validate/pkg/core"
	"validate/pkg/types"
)

// defaultClient is a shared HTTP client for all requests (enables connection pooling)
var defaultClient = &http.Client{
	Timeout: 10 * time.Second,
}

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

	if testCase.TestClass == "dynamic" {
		function_if := GetDynamicTest(testCase.URL)
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

	// Use the new executeUrl function to perform the HTTP request
	resp, responseBody, err := executeUrl(fullURL, testCase.Method, testCase.RequestBody)
	if err != nil {
		return nil, err
	}

	// Reshape response to TestResult format
	result, err := reshapeToTestResult(resp, responseBody, testCase.URL)
	if err != nil {
		return nil, err
	}

	// Parse URL parameters from the full URL
	params, err := parseTestURL(fullURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL parameters: %w", err)
	}
	result.Params = *params

	return result, nil
}

// parseTestURL extracts test parameters from a URL string (simplified version)
func parseTestURL(urlStr string) (*types.TestParams, error) {
	u, err := url.Parse(urlStr)
	if err != nil {
		return nil, fmt.Errorf("invalid URL: %w", err)
	}

	params := &types.TestParams{
		Sort:        []types.SortField{},
		Filter:      make(map[string][]types.FilterValue),
		FilterMatch: "substring", // default to substring matching
		View:        make(map[string][]string),
		Page:        1,
		PageSize:    25,
	}

	query := u.Query()

	// For duplicate parameters, last value wins
	for key, values := range query {
		lastValue := values[len(values)-1]

		switch strings.ToLower(key) {
		case "page":
			if page, err := strconv.Atoi(lastValue); err == nil {
				params.Page = page
			}
		case "pagesize":
			if pageSize, err := strconv.Atoi(lastValue); err == nil {
				params.PageSize = pageSize
			}
		case "sort":
			params.Sort = parseSortParam(lastValue)
		case "filter":
			params.Filter = parseFilterParam(lastValue)
		case "filter_match":
			if lastValue == "" || lastValue == "substring" || lastValue == "full" {
				if lastValue == "" {
					params.FilterMatch = "substring"
				} else {
					params.FilterMatch = lastValue
				}
			}
		case "view":
			params.View = parseViewParam(lastValue)
		}
	}

	return params, nil
}

// parseSortParam parses sort parameter like "firstName:desc,lastName:asc"
func parseSortParam(sortStr string) []types.SortField {
	var sortFields []types.SortField

	for _, fieldSpec := range strings.Split(sortStr, ",") {
		fieldSpec = strings.TrimSpace(fieldSpec)
		if fieldSpec == "" {
			continue
		}

		// Check for field:direction format
		parts := strings.Split(fieldSpec, ":")
		field := strings.TrimSpace(parts[0])
		direction := "asc" // default

		if len(parts) > 1 {
			dir := strings.ToLower(strings.TrimSpace(parts[1]))
			if dir == "desc" || dir == "asc" {
				direction = dir
			}
		}

		if field != "" {
			sortFields = append(sortFields, types.SortField{
				Field:     field,
				Direction: direction,
			})
		}
	}

	return sortFields
}

// parseFilterParam parses filter parameter like "lastName:Smith,age:gte:21"
func parseFilterParam(filterStr string) map[string][]types.FilterValue {
	filters := make(map[string][]types.FilterValue)

	for _, filterPart := range strings.Split(filterStr, ",") {
		filterPart = strings.TrimSpace(filterPart)
		if filterPart == "" {
			continue
		}

		// Split by colon - minimum 2 parts (field:value)
		parts := strings.SplitN(filterPart, ":", 3)
		if len(parts) < 2 {
			continue
		}

		field := strings.TrimSpace(parts[0])
		if field == "" {
			continue
		}

		var operator string
		var value string

		if len(parts) == 2 {
			// Simple format: field:value
			operator = "eq"
			value = strings.TrimSpace(parts[1])
		} else {
			// Extended format: field:operator:value
			operator = strings.ToLower(strings.TrimSpace(parts[1]))
			value = strings.TrimSpace(parts[2])
		}

		// Convert value to appropriate type
		var typedValue interface{} = value
		if intVal, err := strconv.Atoi(value); err == nil {
			typedValue = intVal
		} else if floatVal, err := strconv.ParseFloat(value, 64); err == nil {
			typedValue = floatVal
		} else if boolVal, err := strconv.ParseBool(value); err == nil {
			typedValue = boolVal
		}

		filters[field] = append(filters[field], types.FilterValue{
			Operator: operator,
			Value:    typedValue,
		})
	}

	return filters
}

// parseViewParam parses view parameter like "account(id,name),profile(firstName,lastName)"
func parseViewParam(viewStr string) map[string][]string {
	viewSpec := make(map[string][]string)

	// Find all entity(field1,field2) patterns
	parts := strings.Split(viewStr, ")")
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}

		// Find the opening parenthesis
		parenIndex := strings.Index(part, "(")
		if parenIndex == -1 {
			continue
		}

		entity := strings.TrimSpace(part[:parenIndex])
		fieldsStr := strings.TrimSpace(part[parenIndex+1:])

		if entity == "" || fieldsStr == "" {
			continue
		}

		// Parse fields
		var fields []string
		for _, field := range strings.Split(fieldsStr, ",") {
			field = strings.TrimSpace(field)
			if field != "" {
				fields = append(fields, field)
			}
		}

		if len(fields) > 0 {
			viewSpec[entity] = fields
		}
	}

	return viewSpec
}

// executeUrl abstracts HTTP calls - hides all HTTP internals from callers
func executeUrl(fullURL, method string, body interface{}) (*http.Response, []byte, error) {
	// Use shared HTTP client for connection pooling
	client := defaultClient

	// Prepare request body if present
	var requestBody io.Reader
	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return nil, nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		requestBody = bytes.NewReader(jsonBody)
	}

	// Execute the HTTP request
	req, err := http.NewRequest(method, fullURL, requestBody)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to create request: %w", err)
	}

	// Set content type for POST/PUT requests with body
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	// Add session cookie if authenticated
	if core.SessionID != "" {
		req.Header.Set("Cookie", "sessionId="+core.SessionID)
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to execute request: %w", err)
	}
	defer resp.Body.Close()

	// Read response body
	responseBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to read response body: %w", err)
	}

	return resp, responseBody, nil
}

// reshapeToTestResult converts raw HTTP response to TestResult format
func reshapeToTestResult(resp *http.Response, responseBody []byte, url string) (*types.TestResult, error) {
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

	// Check if database is Elasticsearch to determine if pause is needed
	// dbType := core.GetDatabaseType()
	// usePause := (dbType == "elasticsearch") && (core.PauseMs > 0)

	results := make([]*types.TestResult, len(testNumbers))

	lastUpdate := time.Now()
	showing_progress := false

	for i, testNum := range testNumbers {
		// Show progress update if using pause and more than 1 second since last update
		// if usePause {
		now := time.Now()
		if now.Sub(lastUpdate) > 1*time.Second {
			fmt.Fprintf(os.Stderr, "\rRunning test %d  ", testNum)
			lastUpdate = now
			showing_progress = true
		}
		// }

		// Execute test
		result, err := ExecuteTest(testNum)
		results[i] = result

		// Pause between tests if using Elasticsearch (for eventual consistency)
		// if usePause && i < len(testNumbers)-1 {
		// 	time.Sleep(time.Duration(core.PauseMs) * time.Millisecond)
		// }

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
