package dynamic

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"validate/pkg/core"
	"validate/pkg/types"
)

func testPaginationDefault() (*types.TestResult, error) {
	return testPaginationAggregation("")
}

func testPaginationById() (*types.TestResult, error) {
	return testPaginationAggregation("id")
}

func testPaginationByUserName() (*types.TestResult, error) {
	return testPaginationAggregation("username")
}

// testPaginationAggregation validates that pagination is working correctly
func testPaginationAggregation(key string) (*types.TestResult, error) {
	// Use default id field if key is empty
	if key == "" {
		key = "id"
	}

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
	allRecords, pageCount, err := fetchAllPages(client, pageSize, key)
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

	// Step 5: Validate sort key field is unique and in order
	seenKeyValues := make(map[interface{}]bool)
	var lastKeyValue interface{}
	for i, record := range allRecords {
		keyValue, exists := record[key]
		if !exists {
			result.Issues = append(result.Issues, fmt.Sprintf("Record %d missing '%s' field", i, key))
			continue
		}

		// Check for duplicate key values
		if seenKeyValues[keyValue] {
			result.Issues = append(result.Issues, fmt.Sprintf("Duplicate %s found: %v", key, keyValue))
		}
		seenKeyValues[keyValue] = true

		// Step 6: Validate sort key values are in increasing order
		if i > 0 {
			comparison := compareValues(lastKeyValue, keyValue)
			if comparison >= 0 { // lastKeyValue should be < keyValue for ascending order
				result.Issues = append(result.Issues, fmt.Sprintf("%s not in increasing order: %v followed by %v at index %d", key, lastKeyValue, keyValue, i))
			}
		}
		lastKeyValue = keyValue
	}

	// Create synthetic summary data
	result.Data = []map[string]interface{}{
		{
			"totalRecords":    len(allRecords),
			"expectedRecords": totalUsers,
			"pageCount":       pageCount,
			"expectedPages":   expectedPageCount,
			"uniqueValues":    len(seenKeyValues),
			"sortKey":         key,
			"sortOrder":       "ascending",
		},
	}

	// Set Passed based on whether any issues were found
	result.Passed = len(result.Issues) == 0
	return result, nil
}

// fetchAllPages fetches all user pages with the given pageSize
func fetchAllPages(client *http.Client, pageSize int, key string) ([]map[string]interface{}, int, error) {
	var allRecords []map[string]interface{}
	page := 1
	totalPages := 0

	for {
		var url string
		if key == "" {
			url = fmt.Sprintf("%s/api/User?page=%d&pageSize=%d", core.ServerURL, page, pageSize)
		} else {
			url = fmt.Sprintf("%s/api/User?sort=%s&page=%d&pageSize=%d", core.ServerURL, key, page, pageSize)
		}
		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			return nil, 0, err
		}

		// Add session cookie if available
		if core.SessionID != "" {
			req.Header.Set("Cookie", "sessionId="+core.SessionID)
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
