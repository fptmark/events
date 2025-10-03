package httpclient

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
	"validate/pkg/datagen"
	"validate/pkg/dynamic"
	"validate/pkg/tests"
	"validate/pkg/types"
)

// HTTPExecutor executes API tests in real-time
type HTTPExecutor struct {
	client  *http.Client
	dbReset bool // tracks if database has been reset for this session
}

// NewHTTPExecutor creates a new HTTP executor
func NewHTTPExecutor() *HTTPExecutor {
	return &HTTPExecutor{
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
		dbReset: false,
	}
}

// ExecuteTest executes a test by number and returns TestResult
func (e *HTTPExecutor) ExecuteTest(testNumber int) (*core.TestResult, error) {
	// Get test definition from static test suite
	allTests := tests.GetAllTestCases()
	testCase := allTests[testNumber-1] // testNumber is 1-based

	if testCase.TestClass == "dynamic" {
		function_if := dynamic.GetFunction(testCase.URL)
		if function_if == nil {
			fmt.Fprintf(os.Stderr, "no dynamic function found for URL: %s\n", testCase.URL)
			os.Exit(1)
		}
		result, err := function_if()
		return result, err
	}

	// Execute the test
	executedTestCase, err := e.executeTestCase(&testCase)
	if err != nil {
		return nil, err
	}

	// Convert to core.TestResult format
	result := &core.TestResult{
		ID:              executedTestCase.ID,
		URL:             executedTestCase.URL,
		Description:     executedTestCase.Description,
		TestClass:       executedTestCase.TestClass,
		Data:            executedTestCase.Result.Data,
		RawResponseBody: executedTestCase.RawResponseBody,
		Notifications:   executedTestCase.Result.Notifications,
		Status:          executedTestCase.Result.Status,
		StatusCode:      executedTestCase.ActualStatus,
		Params: core.TestParams{
			Sort:   executedTestCase.Params.Sort,
			Filter: executedTestCase.Params.Filter,
			Page:   executedTestCase.Params.Page,
			Size:   executedTestCase.Params.PageSize,
			View:   executedTestCase.Params.View,
		},
	}

	return result, nil
}

// executeTestCase executes a single test case and returns a TestCase compatible with existing code
func (e *HTTPExecutor) executeTestCase(testCase *types.TestCase) (*types.TestCase, error) {
	// Build full URL using GlobalConfig.ServerURL
	fullURL := datagen.GlobalConfig.ServerURL + testCase.URL

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

	// Convert the TestResult back to TestCase format for compatibility
	testCase.ActualStatus = result.StatusCode
	testCase.RawResponseBody = result.RawResponseBody
	testCase.Result = types.TestResult{
		Status:        result.Status,
		Data:         result.Data,
		Notifications: result.Notifications,
	}

	// Parse URL parameters from the full URL
	params, err := parseTestURL(fullURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL parameters: %w", err)
	}
	testCase.Params = *params

	return testCase, nil
}

// formatResponse formats the HTTP response to match the results.json structure
func (e *HTTPExecutor) formatResponse(responseData interface{}, statusCode int) types.TestResult {
	result := types.TestResult{
		Data:          []map[string]interface{}{},
		Notifications: nil,
		Status:        fmt.Sprintf("%d", statusCode),
	}

	// Handle different response types
	if responseMap, ok := responseData.(map[string]interface{}); ok {
		// Standard API response format
		if dataVal, exists := responseMap["data"]; exists {
			switch d := dataVal.(type) {
			case []interface{}:
				// Array of objects (collection response)
				for _, item := range d {
					if itemMap, ok := item.(map[string]interface{}); ok {
						result.Data = append(result.Data, itemMap)
					}
				}
			case map[string]interface{}:
				// Single object (individual resource response)
				result.Data = append(result.Data, d)
			case nil:
				// Handle null data
				result.Data = []map[string]interface{}{}
			}
		}

		// Extract notifications
		if notifVal, exists := responseMap["notifications"]; exists {
			result.Notifications = notifVal
		}

		// Extract status from response if available
		if statusVal, exists := responseMap["status"]; exists {
			if statusStr, ok := statusVal.(string); ok {
				result.Status = statusStr
			}
		}
	} else {
		// Non-standard response (error, plain text, etc.)
		result.Status = fmt.Sprintf("%d %v", statusCode, responseData)
		result.Data = []map[string]interface{}{}
		result.Notifications = nil
	}

	return result
}

// GetAllTests returns all static test cases
func (e *HTTPExecutor) GetAllTests() []types.TestCase {
	return tests.GetAllTestCases()
}

// CountTests returns the total number of tests
func (e *HTTPExecutor) CountTests() int {
	return len(tests.GetAllTestCases())
}

// parseTestURL extracts test parameters from a URL string (simplified version)
func parseTestURL(urlStr string) (*types.TestParams, error) {
	u, err := url.Parse(urlStr)
	if err != nil {
		return nil, fmt.Errorf("invalid URL: %w", err)
	}

	params := &types.TestParams{
		Sort:     []types.SortField{},
		Filter:   make(map[string][]types.FilterValue),
		View:     make(map[string][]string),
		Page:     1,
		PageSize: 25,
	}

	query := u.Query()

	// Parse page
	if pageStr := query.Get("page"); pageStr != "" {
		if page, err := strconv.Atoi(pageStr); err == nil && page > 0 {
			params.Page = page
		}
	}

	// Parse pageSize
	if pageSizeStr := query.Get("pageSize"); pageSizeStr != "" {
		if pageSize, err := strconv.Atoi(pageSizeStr); err == nil && pageSize > 0 {
			params.PageSize = pageSize
		}
	}

	// Parse sort parameter
	if sortStr := query.Get("sort"); sortStr != "" {
		params.Sort = parseSortParam(sortStr)
	}

	// Parse filter parameter
	if filterStr := query.Get("filter"); filterStr != "" {
		params.Filter = parseFilterParam(filterStr)
	}

	// Parse view parameter
	if viewStr := query.Get("view"); viewStr != "" {
		params.View = parseViewParam(viewStr)
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
	// Use static HTTP client for performance
	client := &http.Client{Timeout: 10 * time.Second}

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
func reshapeToTestResult(resp *http.Response, responseBody []byte, url string) (*core.TestResult, error) {
	// Parse the response body as JSON
	var responseData interface{}
	if err := json.Unmarshal(responseBody, &responseData); err != nil {
		// If JSON parsing fails, treat as error response
		responseData = string(responseBody)
	}

	// Create base result
	result := &core.TestResult{
		URL:             url,
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

		// Extract status from response if available
		if statusVal, exists := responseMap["status"]; exists {
			if statusStr, ok := statusVal.(string); ok {
				result.Status = statusStr
			}
		}
	} else {
		// Non-standard response (error, plain text, etc.)
		result.Status = fmt.Sprintf("%d", resp.StatusCode)
		result.Data = []map[string]interface{}{}
		result.Notifications = nil
	}

	if result.Status == "" {
		result.Status = fmt.Sprintf("%d", resp.StatusCode)
	}

	return result, nil
}

// ExecuteTest is a package-level function that creates an executor and runs a test
func ExecuteTest(testNumber int) (*core.TestResult, error) {
	executor := NewHTTPExecutor()
	return executor.ExecuteTest(testNumber)
}

// ensureDatabaseReset ensures the database is reset exactly once per test session
func (e *HTTPExecutor) ensureDatabaseReset() error {
	if e.dbReset {
		return nil // Already reset
	}

	fmt.Println("Resetting database...")

	// Step 1: Call api/db/report to get initial counts
	fmt.Println("Getting initial database counts...")
	if err := e.callDatabaseReport("Initial"); err != nil {
		return fmt.Errorf("failed to get initial database report: %w", err)
	}

	// Step 2: Call api/db/init to clear all data
	fmt.Println("Clearing database...")
	if err := e.callDatabaseInit(); err != nil {
		return fmt.Errorf("failed to initialize database: %w", err)
	}

	// Step 3: Call api/db/report again to confirm clearing
	fmt.Println("Getting database counts after clearing...")
	if err := e.callDatabaseReport("After clearing"); err != nil {
		return fmt.Errorf("failed to get database report after clearing: %w", err)
	}

	e.dbReset = true
	fmt.Println("Database reset complete.\n")
	return nil
}

// callDatabaseReport calls api/db/report and displays only the counts
func (e *HTTPExecutor) callDatabaseReport(stage string) error {
	req, err := http.NewRequest("GET", datagen.GlobalConfig.ServerURL+"/api/db/report", nil)
	if err != nil {
		return err
	}

	resp, err := e.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	var reportData map[string]interface{}
	if err := json.Unmarshal(body, &reportData); err == nil {
		// Extract counts from report.entities
		if report, exists := reportData["report"]; exists {
			if reportMap, ok := report.(map[string]interface{}); ok {
				if entities, exists := reportMap["entities"]; exists {
					if entitiesMap, ok := entities.(map[string]interface{}); ok {
						fmt.Printf("%s counts: ", stage)
						for table, count := range entitiesMap {
							fmt.Printf("%s=%v ", table, count)
						}
						fmt.Println()
					}
				}
			}
		}
	} else {
		fmt.Printf("%s counts: (parse error)\n", stage)
	}

	return nil
}

// callDatabaseInit calls api/db/init to clear all data
func (e *HTTPExecutor) callDatabaseInit() error {
	req, err := http.NewRequest("POST", datagen.GlobalConfig.ServerURL+"/api/db/init", nil)
	if err != nil {
		return err
	}

	resp, err := e.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("database init failed with status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}
