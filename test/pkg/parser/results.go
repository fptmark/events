package parser

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"strconv"
	"strings"

	"query-verify/pkg/types"
)

// LoadTestCase loads a specific test case from results.json using jq
func LoadTestCase(testID int, resultsFile string) (*types.TestCase, error) {
	// First get all keys in original order to find the test by index
	cmd := exec.Command("jq", "-r", "keys_unsorted[]", resultsFile)
	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to get test keys: %w", err)
	}

	keys := strings.Split(strings.TrimSpace(string(output)), "\n")
	if testID < 1 || testID > len(keys) {
		return nil, fmt.Errorf("test ID %d out of range (1-%d)", testID, len(keys))
	}

	// Get the URL key for this test
	testURL := keys[testID-1]

	// Extract the test case using the URL key
	cmd = exec.Command("jq", fmt.Sprintf(".[\"%s\"]", strings.ReplaceAll(testURL, "\"", "\\\"")), resultsFile)
	output, err = cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to extract test case for URL %s: %w", testURL, err)
	}

	var rawTest map[string]interface{}
	if err := json.Unmarshal(output, &rawTest); err != nil {
		return nil, fmt.Errorf("failed to parse test case JSON: %w", err)
	}

	// Parse the test case
	testCase := &types.TestCase{
		ID: testID,
	}

	// Extract URL (use the key as URL, or extract from data if available)
	if urlVal, ok := rawTest["url"].(string); ok {
		testCase.URL = urlVal
	} else {
		// Use the key as URL if no url field in data
		testCase.URL = testURL
	}

	// Extract method
	if methodVal, ok := rawTest["method"].(string); ok {
		testCase.Method = methodVal
	}

	// Extract description
	if descVal, ok := rawTest["description"].(string); ok {
		testCase.Description = descVal
	}

	// Parse URL parameters
	params, err := ParseTestURL(testCase.URL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse URL parameters: %w", err)
	}
	testCase.Params = *params

	// Extract result from response field
	result := types.TestResult{}

	// Handle different response types - can be object or string (for errors)
	if responseVal, ok := rawTest["response"].(map[string]interface{}); ok {
		// Parse data - can be array or single object
		if dataVal, ok := responseVal["data"]; ok {
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

		// Parse notifications - keep raw structure to preserve complex nested warnings
		if notifVal, ok := responseVal["notifications"]; ok {
			result.Notifications = notifVal
		}

		// Parse status
		if statusVal, ok := responseVal["status"].(string); ok {
			result.Status = statusVal
		}
	} else if responseStr, ok := rawTest["response"].(string); ok {
		// Handle error responses that are just strings
		result.Status = responseStr
		result.Data = []map[string]interface{}{}
		result.Notifications = nil
	}

	// Also get HTTP status code
	if statusCode, ok := rawTest["status"].(float64); ok {
		if result.Status != "" {
			result.Status = fmt.Sprintf("%d %s", int(statusCode), result.Status)
		} else {
			result.Status = fmt.Sprintf("%d", int(statusCode))
		}
	}

	testCase.Result = result

	return testCase, nil
}

// CountTests returns the number of tests in results.json
func CountTests(resultsFile string) (int, error) {
	cmd := exec.Command("jq", "keys_unsorted | length", resultsFile)
	output, err := cmd.Output()
	if err != nil {
		return 0, fmt.Errorf("failed to count tests: %w", err)
	}

	countStr := strings.TrimSpace(string(output))
	count, err := strconv.Atoi(countStr)
	if err != nil {
		return 0, fmt.Errorf("failed to parse test count: %w", err)
	}

	return count, nil
}

// ExtractVerificationFields extracts relevant fields from test results based on parameters
func ExtractVerificationFields(testCase *types.TestCase) *types.FieldExtraction {
	extraction := &types.FieldExtraction{
		SortFields:   make(map[string][]interface{}),
		FilterFields: make(map[string][]interface{}),
		ViewFields:   make(map[string][]interface{}),
	}

	// Extract sort fields
	for _, sortField := range testCase.Params.Sort {
		fieldName := sortField.Field
		values := extractFieldValues(testCase.Result.Data, fieldName)
		extraction.SortFields[fieldName] = values
	}

	// Extract filter fields
	for fieldName := range testCase.Params.Filter {
		values := extractFieldValues(testCase.Result.Data, fieldName)
		extraction.FilterFields[fieldName] = values
	}

	// Extract view fields
	for entity, fields := range testCase.Params.View {
		for _, fieldName := range fields {
			// Look for the field in the main data or in nested objects
			values := extractNestedFieldValues(testCase.Result.Data, entity, fieldName)
			if len(values) > 0 {
				extraction.ViewFields[fmt.Sprintf("%s.%s", entity, fieldName)] = values
			}
		}
	}

	return extraction
}

// extractFieldValues extracts all values for a specific field from the data array
func extractFieldValues(data []map[string]interface{}, fieldName string) []interface{} {
	var values []interface{}

	for _, item := range data {
		if value, exists := item[fieldName]; exists {
			values = append(values, value)
		}
	}

	return values
}

// extractNestedFieldValues extracts values from nested objects (for view fields)
func extractNestedFieldValues(data []map[string]interface{}, entity, fieldName string) []interface{} {
	var values []interface{}

	for _, item := range data {
		// Look for the entity as a nested object
		if entityData, exists := item[entity]; exists {
			if entityMap, ok := entityData.(map[string]interface{}); ok {
				if value, exists := entityMap[fieldName]; exists {
					values = append(values, value)
				}
			}
		}

		// Also check if the field exists directly (in case of flattened data)
		fullFieldName := fmt.Sprintf("%s.%s", entity, fieldName)
		if value, exists := item[fullFieldName]; exists {
			values = append(values, value)
		}
	}

	return values
}