package tests

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"validate/pkg/core"
	"validate/pkg/types"
)

// Map of dynamic test function names to function pointers
var dynamicTests = map[string]func() (*types.TestResult, error){
	"testPaginationAggregation": testPaginationAggregation,
	"testMetadata":              testMetadata,
	"testDbReport":              testDbReport,
	"testDbInit":                testDbInit,
	"testAuth":                  testAuth,
}

// GetDynamicTest returns the dynamic test function for the given name, or nil if not found
func GetDynamicTest(functionName string) func() (*types.TestResult, error) {
	if fn, exists := dynamicTests[functionName]; exists {
		return fn
	}
	return nil
}

// testPaginationAggregation validates that pagination is working correctly
func testPaginationAggregation() (*types.TestResult, error) {
	client := &http.Client{Timeout: 10 * time.Second}

	// Create result that will be returned in all cases
	result := &types.TestResult{
		StatusCode: 200,
		Data:       []map[string]interface{}{},
		Issues:     []string{},
		Fields:     make(map[string][]interface{}),
		Passed:     false, // Will be set to true only if all validations pass
	}

	// Step 1: Get total user count from db/report endpoint
	totalUsers, _ := core.GetEntityCountsFromReport()

	// Step 2: Fetch all pages with pageSize=8
	pageSize := 8
	allRecords, pageCount, err := fetchAllPages(client, pageSize)
	if err != nil {
		// Return error for execution failures (can't connect, etc.)
		return result, fmt.Errorf("failed to fetch all pages: %w", err)
	}

	// Calculate expected page count
	expectedPageCount := (totalUsers + pageSize - 1) / pageSize // ceiling division

	// Step 3: Verify page count matches expected
	if pageCount != expectedPageCount {
		result.Issues = append(result.Issues, fmt.Sprintf("Page count mismatch: expected %d pages, got %d pages", expectedPageCount, pageCount))
	}

	// Step 4: Verify total records fetched equals total user count
	if len(allRecords) != totalUsers {
		result.Issues = append(result.Issues, fmt.Sprintf("Record count mismatch: expected %d records, got %d records", totalUsers, len(allRecords)))
	}

	// Step 5: Validate all user IDs are unique
	seenIDs := make(map[interface{}]bool)
	var lastID interface{}
	for i, record := range allRecords {
		id, exists := record["id"]
		if !exists {
			result.Issues = append(result.Issues, fmt.Sprintf("Record %d missing 'id' field", i))
			continue
		}

		// Check for duplicates
		if seenIDs[id] {
			result.Issues = append(result.Issues, fmt.Sprintf("Duplicate ID found: %v", id))
		}
		seenIDs[id] = true

		// Step 6: Validate IDs are increasing (default sort order)
		if i > 0 {
			if !isIDIncreasing(lastID, id) {
				result.Issues = append(result.Issues, fmt.Sprintf("IDs not in increasing order: %v followed by %v at index %d", lastID, id, i))
			}
		}
		lastID = id
	}

	// Create synthetic summary data
	result.Data = []map[string]interface{}{
		{
			"totalRecords":   len(allRecords),
			"expectedRecords": totalUsers,
			"pageCount":      pageCount,
			"expectedPages":  expectedPageCount,
			"uniqueIDs":      len(seenIDs),
			"sortOrder":      "ascending",
		},
	}

	// Set Passed based on whether any issues were found
	result.Passed = len(result.Issues) == 0
	return result, nil
}

// fetchAllPages fetches all user pages with the given pageSize
func fetchAllPages(client *http.Client, pageSize int) ([]map[string]interface{}, int, error) {
	var allRecords []map[string]interface{}
	page := 1
	totalPages := 0

	for {
		url := fmt.Sprintf("%s/api/User?page=%d&pageSize=%d", core.ServerURL, page, pageSize)
		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			return nil, 0, err
		}

		resp, err := client.Do(req)
		if err != nil {
			return nil, 0, err
		}

		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			return nil, 0, err
		}

		var responseData map[string]interface{}
		if err := json.Unmarshal(body, &responseData); err != nil {
			return nil, 0, err
		}

		// Extract data array
		dataArray, ok := responseData["data"].([]interface{})
		if !ok {
			return nil, 0, fmt.Errorf("invalid data structure on page %d", page)
		}

		// Extract pagination info
		pagination, ok := responseData["pagination"].(map[string]interface{})
		if !ok {
			return nil, 0, fmt.Errorf("missing pagination on page %d", page)
		}

		totalPages = int(pagination["totalPages"].(float64))

		// Add records from this page
		for _, item := range dataArray {
			if record, ok := item.(map[string]interface{}); ok {
				allRecords = append(allRecords, record)
			}
		}

		// Check if we've fetched all pages
		if page >= totalPages {
			break
		}

		page++
	}

	return allRecords, totalPages, nil
}

// isIDIncreasing checks if id2 > id1
func isIDIncreasing(id1, id2 interface{}) bool {
	// Handle string IDs
	str1, ok1 := id1.(string)
	str2, ok2 := id2.(string)
	if ok1 && ok2 {
		return str2 > str1
	}

	// Handle numeric IDs
	num1, ok1 := id1.(float64)
	num2, ok2 := id2.(float64)
	if ok1 && ok2 {
		return num2 > num1
	}

	// Fallback: convert to string and compare
	return fmt.Sprintf("%v", id2) > fmt.Sprintf("%v", id1)
}

// testAdminEndpoint is a generic test for admin endpoints - validates 200 status and expected data type
func testAdminEndpoint(url string, dataType string) (*types.TestResult, error) {
	result := &types.TestResult{
		StatusCode: 200,
		Data:       []map[string]interface{}{},
		Issues:     []string{},
		Fields:     make(map[string][]interface{}),
		Passed:     false,
	}

	fullURL := core.ServerURL + url
	resp, body, err := executeUrl(fullURL, "GET", nil)
	if err != nil {
		return result, fmt.Errorf("failed to execute request: %w", err)
	}

	result.StatusCode = resp.StatusCode

	if resp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Expected status 200, got %d", resp.StatusCode))
		return result, nil
	}

	// Check if response matches expected data type
	var responseData interface{}
	isJSON := json.Unmarshal(body, &responseData) == nil

	if dataType == "JSON" && !isJSON {
		result.Issues = append(result.Issues, "Expected JSON response but got non-JSON content")
	} else if dataType == "HTML" && isJSON {
		result.Issues = append(result.Issues, "Expected HTML response but got JSON content")
	}

	result.Data = []map[string]interface{}{
		{
			"endpoint":     url,
			"statusCode":   resp.StatusCode,
			"expectedType": dataType,
			"isJSON":       isJSON,
		},
	}

	result.Passed = len(result.Issues) == 0
	return result, nil
}

// testMetadata validates /api/metadata endpoint (expects JSON)
func testMetadata() (*types.TestResult, error) {
	return testAdminEndpoint("/api/metadata", "JSON")
}

// testDbReport validates /api/db/report endpoint (expects JSON)
func testDbReport() (*types.TestResult, error) {
	return testAdminEndpoint("/api/db/report", "JSON")
}

// testDbInit validates /api/db/init endpoint (expects HTML)
func testDbInit() (*types.TestResult, error) {
	return testAdminEndpoint("/api/db/init", "HTML")
}

// testAuth validates the complete Redis authentication workflow
func testAuth() (*types.TestResult, error) {
	client := &http.Client{
		Timeout: 10 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse // Don't follow redirects
		},
	}

	result := &types.TestResult{
		StatusCode: 200,
		Data:       []map[string]interface{}{},
		Issues:     []string{},
		Fields:     make(map[string][]interface{}),
		Passed:     false,
	}

	// Step 1: Login with valid credentials
	loginBody := map[string]interface{}{
		"username": "mark",
		"password": "12345678",
	}
	loginResp, loginRespBody, err := executeAuthRequest(client, "/user/auth/login", "POST", loginBody, "")
	if err != nil {
		return result, fmt.Errorf("login request failed: %w", err)
	}

	if loginResp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Login failed: expected 200, got %d", loginResp.StatusCode))
		return result, nil
	}

	// Extract session cookie
	var sessionID string
	for _, cookie := range loginResp.Cookies() {
		if cookie.Name == "sessionId" {
			sessionID = cookie.Value
			break
		}
	}

	if sessionID == "" {
		result.Issues = append(result.Issues, "Login succeeded but no sessionId cookie returned")
		return result, nil
	}

	// Verify login response body
	var loginData map[string]interface{}
	if err := json.Unmarshal(loginRespBody, &loginData); err != nil {
		result.Issues = append(result.Issues, "Login response is not valid JSON")
	} else {
		if success, ok := loginData["success"].(bool); !ok || !success {
			result.Issues = append(result.Issues, "Login response missing success=true")
		}
	}

	// Step 2: Test refresh with session cookie
	refreshResp, refreshRespBody, err := executeAuthRequest(client, "/user/auth/refresh", "POST", nil, sessionID)
	if err != nil {
		return result, fmt.Errorf("refresh request failed: %w", err)
	}

	if refreshResp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Refresh failed: expected 200, got %d", refreshResp.StatusCode))
	}

	var refreshData map[string]interface{}
	if err := json.Unmarshal(refreshRespBody, &refreshData); err != nil {
		result.Issues = append(result.Issues, "Refresh response is not valid JSON")
	} else {
		if success, ok := refreshData["success"].(bool); !ok || !success {
			result.Issues = append(result.Issues, "Refresh response missing success=true")
		}
	}

	// Step 3: Logout with session cookie
	logoutResp, logoutRespBody, err := executeAuthRequest(client, "/user/auth/logout", "POST", nil, sessionID)
	if err != nil {
		return result, fmt.Errorf("logout request failed: %w", err)
	}

	if logoutResp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Logout failed: expected 200, got %d", logoutResp.StatusCode))
	}

	var logoutData map[string]interface{}
	if err := json.Unmarshal(logoutRespBody, &logoutData); err != nil {
		result.Issues = append(result.Issues, "Logout response is not valid JSON")
	} else {
		if success, ok := logoutData["success"].(bool); !ok || !success {
			result.Issues = append(result.Issues, "Logout response missing success=true")
		}
	}

	// Step 4: Try refresh after logout (should fail)
	postLogoutResp, postLogoutRespBody, err := executeAuthRequest(client, "/user/auth/refresh", "POST", nil, sessionID)
	if err != nil {
		return result, fmt.Errorf("post-logout refresh request failed: %w", err)
	}

	// Check if refresh after logout fails (returns null or success=false)
	var postLogoutData map[string]interface{}
	if err := json.Unmarshal(postLogoutRespBody, &postLogoutData); err != nil || postLogoutData == nil {
		// null response or invalid JSON is expected for failed refresh
	} else {
		if success, ok := postLogoutData["success"].(bool); ok && success {
			result.Issues = append(result.Issues, "Refresh after logout should not return success=true")
		}
	}

	// Step 5: Test invalid credentials
	badLoginBody := map[string]interface{}{
		"username": "mark",
		"password": "wrongpassword",
	}
	badLoginResp, badLoginRespBody, err := executeAuthRequest(client, "/user/auth/login", "POST", badLoginBody, "")
	if err != nil {
		return result, fmt.Errorf("bad login request failed: %w", err)
	}

	// Check if login with invalid credentials fails (returns null or success=false)
	var badLoginData map[string]interface{}
	if err := json.Unmarshal(badLoginRespBody, &badLoginData); err != nil || badLoginData == nil {
		// null response or invalid JSON is expected for failed login
	} else {
		if success, ok := badLoginData["success"].(bool); ok && success {
			result.Issues = append(result.Issues, "Invalid credentials should not return success=true")
		}
	}

	// Create summary data
	result.Data = []map[string]interface{}{
		{
			"loginStatus":          loginResp.StatusCode,
			"sessionIdReceived":    sessionID != "",
			"refreshStatus":        refreshResp.StatusCode,
			"logoutStatus":         logoutResp.StatusCode,
			"postLogoutStatus":     postLogoutResp.StatusCode,
			"badCredentialsStatus": badLoginResp.StatusCode,
		},
	}

	result.Passed = len(result.Issues) == 0
	return result, nil
}

// executeAuthRequest helper for auth endpoints with cookie handling
func executeAuthRequest(client *http.Client, path string, method string, body map[string]interface{}, sessionID string) (*http.Response, []byte, error) {
	url := core.ServerURL + path

	var bodyReader io.Reader
	if body != nil {
		bodyBytes, err := json.Marshal(body)
		if err != nil {
			return nil, nil, err
		}
		bodyReader = bytes.NewReader(bodyBytes)
	}

	req, err := http.NewRequest(method, url, bodyReader)
	if err != nil {
		return nil, nil, err
	}

	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	// Add session cookie if provided
	if sessionID != "" {
		req.AddCookie(&http.Cookie{
			Name:  "sessionId",
			Value: sessionID,
		})
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, nil, err
	}

	respBody, err := io.ReadAll(resp.Body)
	resp.Body.Close()
	if err != nil {
		return resp, nil, err
	}

	return resp, respBody, nil
}
