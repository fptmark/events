package tests

import (
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
