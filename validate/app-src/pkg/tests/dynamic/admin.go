package dynamic

import (
	"encoding/json"
	"fmt"

	"validate/pkg/core"
	"validate/pkg/types"
)

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
