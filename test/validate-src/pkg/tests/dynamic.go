package tests

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"validate/pkg/datagen"
	"validate/pkg/types"
)

// Map of dynamic test function names to function pointers
var dynamicTests = map[string]func() (*types.TestResult, error){
	"testPaginationAggregation": testPaginationAggregation,
	// Add more dynamic tests here as needed
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

	// Step 1: Get total user count from db/report endpoint
	totalUsers, err := datagen.GetEntityCountFromReport("User")
	if err != nil {
		return nil, fmt.Errorf("failed to get total user count: %w", err)
	}

	// Step 2: Fetch all pages with pageSize=8
	pageSize := 8
	allRecords, pageCount, err := fetchAllPages(client, pageSize)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch all pages: %w", err)
	}

	// Calculate expected page count
	expectedPageCount := (totalUsers + pageSize - 1) / pageSize // ceiling division

	// Create result
	result := &types.TestResult{
		StatusCode: 200,
		Data:       []map[string]interface{}{},
	}

	// Step 3: Verify page count matches expected
	if pageCount != expectedPageCount {
		return nil, fmt.Errorf("page count mismatch: expected %d pages, got %d pages", expectedPageCount, pageCount)
	}

	// Step 4: Verify total records fetched equals total user count
	if len(allRecords) != totalUsers {
		return nil, fmt.Errorf("record count mismatch: expected %d records, got %d records", totalUsers, len(allRecords))
	}

	// Step 5: Validate all user IDs are unique
	seenIDs := make(map[interface{}]bool)
	var lastID interface{}
	for i, record := range allRecords {
		id, exists := record["id"]
		if !exists {
			return nil, fmt.Errorf("record %d missing 'id' field", i)
		}

		// Check for duplicates
		if seenIDs[id] {
			return nil, fmt.Errorf("duplicate ID found: %v", id)
		}
		seenIDs[id] = true

		// Step 6: Validate IDs are increasing (default sort order)
		if i > 0 {
			if !isIDIncreasing(lastID, id) {
				return nil, fmt.Errorf("IDs not in increasing order: %v followed by %v at index %d", lastID, id, i)
			}
		}
		lastID = id
	}

	// All validations passed
	result.Passed = true
	return result, nil
}

// fetchAllPages fetches all user pages with the given pageSize
func fetchAllPages(client *http.Client, pageSize int) ([]map[string]interface{}, int, error) {
	var allRecords []map[string]interface{}
	page := 1
	totalPages := 0

	for {
		url := fmt.Sprintf("%s/api/User?page=%d&pageSize=%d", datagen.GlobalConfig.ServerURL, page, pageSize)
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
