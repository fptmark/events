package display

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"

	"validate/pkg/core"
	"validate/pkg/httpclient"
	"validate/pkg/tests"
	"validate/pkg/types"
)

// DisplayOptions controls how test results are displayed
type DisplayOptions struct {
	ShowAllData       bool // Show all data records instead of truncating arrays
	ShowNotifications bool // Show all notifications instead of truncating
}

// FormatTestResponse formats a test response according to display options
func FormatTestResponse(testCase *types.TestCase, options DisplayOptions) (string, error) {
	var result strings.Builder

	result.WriteString("Response:\n")

	// Determine data length for truncation logic
	dataLength := len(testCase.Result.Data)
	suppressNotifications := false

	// Determine if we should suppress notifications by default (matching bash logic)
	if dataLength > 1 && !options.ShowNotifications {
		suppressNotifications = true
	}

	// Create a copy of the result to modify
	displayResult := types.TestResult{
		Data:          testCase.Result.Data,
		Notifications: testCase.Result.Notifications,
		Status:        testCase.Result.Status,
	}

	// Handle data truncation
	if !options.ShowAllData && dataLength > 1 {
		displayResult.Data = testCase.Result.Data[:1]
		result.WriteString(fmt.Sprintf("  (Showing first record only, use --data to see all %d records)\n", dataLength))
	}

	// Handle notification truncation
	if suppressNotifications {
		// Get the entity ID from the data to show relevant warnings
		var entityID string
		if len(displayResult.Data) > 0 && displayResult.Data[0] != nil {
			if id, ok := displayResult.Data[0]["id"].(string); ok {
				entityID = id
			}
		}
		// If no data or no ID, entityID will be empty and function will fall back to first entity
		displayResult.Notifications = truncateNotificationsRaw(testCase.Result.Notifications, entityID)
		result.WriteString("  (Warnings truncated to first entity ID per type, use --notify to show all)\n")
	}

	// Use raw interface{} for notifications to preserve the complex nested structure
	var notificationsForDisplay interface{} = displayResult.Notifications

	// Format the JSON response preserving field order when possible
	if len(testCase.RawResponseBody) > 0 {
		// Use raw JSON and apply transformations with jq to preserve field order
		jsonBytes, err := formatWithRawJSON(testCase.RawResponseBody, options, dataLength)
		if err != nil {
			// Fallback to standard formatting if jq fails
			jsonBytes, err := json.MarshalIndent(map[string]interface{}{
				"data":          displayResult.Data,
				"notifications": notificationsForDisplay,
				"status":        displayResult.Status,
			}, "", "  ")
			if err != nil {
				return "", fmt.Errorf("error formatting JSON: %w", err)
			}
			result.WriteString(string(jsonBytes))
		} else {
			result.WriteString(string(jsonBytes))
		}
	} else {
		// Fallback to Go JSON marshaling (will alphabetize fields)
		jsonBytes, err := json.MarshalIndent(map[string]interface{}{
			"data":          displayResult.Data,
			"notifications": notificationsForDisplay,
			"status":        displayResult.Status,
		}, "", "  ")
		if err != nil {
			return "", fmt.Errorf("error formatting JSON: %w", err)
		}
		result.WriteString(string(jsonBytes))
	}
	result.WriteString("\n\n")
	result.WriteString(fmt.Sprintf("URL: %s\n", testCase.URL))
	result.WriteString(fmt.Sprintf("Status: %s\n", displayResult.Status))

	return result.String(), nil
}

// truncateNotificationsRaw truncates the raw notifications structure to show specific entity
func truncateNotificationsRaw(notifications interface{}, targetEntityID string) interface{} {
	if notifications == nil {
		return nil
	}

	// Handle the complex nested structure: notifications.warnings.EntityType.{entityId}
	if notifMap, ok := notifications.(map[string]interface{}); ok {
		if warnings, ok := notifMap["warnings"].(map[string]interface{}); ok {
			truncatedWarnings := make(map[string]interface{})

			// For each entity type (e.g., "User")
			for entityType, entityWarnings := range warnings {
				if entityMap, ok := entityWarnings.(map[string]interface{}); ok {
					truncatedEntityMap := make(map[string]interface{})

					if targetEntityID != "" {
						// Look for the specific entity ID first
						if errors, exists := entityMap[targetEntityID]; exists {
							truncatedEntityMap[targetEntityID] = errors
						}
					} else {
						// Fallback: keep only the first entity ID and all its errors
						for entityID, errors := range entityMap {
							truncatedEntityMap[entityID] = errors
							break // Only keep the first entity ID
						}
					}

					if len(truncatedEntityMap) > 0 {
						truncatedWarnings[entityType] = truncatedEntityMap
					}
				}
			}

			// Return the truncated structure
			return map[string]interface{}{
				"warnings": truncatedWarnings,
			}
		}
	}

	// If structure doesn't match expected format, return as-is
	return notifications
}

// truncateNotificationsWithJQ uses jq to truncate notifications (matching bash script)
func truncateNotificationsWithJQ(testCase *types.TestCase, dataLength int) (types.TestResult, error) {
	// Create the jq filter that matches the bash script logic
	jqFilter := ".response"

	// Truncate data array if needed
	if dataLength > 1 {
		jqFilter += " | if .data | type == \"array\" then .data = [.data[0]] else . end"
	}

	// Truncate notifications (matching bash script)
	jqFilter += " | if .notifications.warnings then .notifications.warnings = (.notifications.warnings | to_entries | map(.value = (.value | to_entries | .[0:1] | from_entries)) | from_entries) else . end"

	// Create temporary JSON for the test case
	tempJSON, err := json.Marshal(map[string]interface{}{
		"response": map[string]interface{}{
			"data":          testCase.Result.Data,
			"notifications": testCase.Result.Notifications,
			"status":        testCase.Result.Status,
		},
	})
	if err != nil {
		return types.TestResult{}, err
	}

	// Apply jq filter
	cmd := exec.Command("jq", jqFilter)
	cmd.Stdin = strings.NewReader(string(tempJSON))
	output, err := cmd.Output()
	if err != nil {
		return types.TestResult{}, err
	}

	// Parse the result back
	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		return types.TestResult{}, err
	}

	// Convert back to TestResult structure
	truncatedResult := types.TestResult{
		Status: testCase.Result.Status,
	}

	// Handle data
	if dataVal, ok := result["data"]; ok {
		switch d := dataVal.(type) {
		case []interface{}:
			for _, item := range d {
				if itemMap, ok := item.(map[string]interface{}); ok {
					truncatedResult.Data = append(truncatedResult.Data, itemMap)
				}
			}
		case map[string]interface{}:
			truncatedResult.Data = append(truncatedResult.Data, d)
		}
	}

	// Handle notifications (keep the raw structure from jq)
	if _, ok := result["notifications"]; ok {
		// Convert the notifications structure to our Notification type
		// For now, this is simplified - the complex nested structure would need proper parsing
		truncatedResult.Notifications = testCase.Result.Notifications
	}

	return truncatedResult, nil
}

// GetTestURL gets the URL for a test by index using jq (matching bash script)
func GetTestURL(resultsFile string, testID int) (string, error) {
	cmd := exec.Command("jq", "-r", fmt.Sprintf("to_entries | .[%d] | .key", testID-1), resultsFile)
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to get URL for test %d: %w", testID, err)
	}

	url := strings.TrimSpace(string(output))
	if url == "null" || url == "" {
		return "", fmt.Errorf("invalid test index %d", testID)
	}

	return url, nil
}

// FormatTableRow formats a single test result as a table row
func FormatTableRow(test types.TestCase, result *core.TestResult, listMode bool) TableRow {
	// Extract URL path (handle both absolute and relative URLs)
	urlPath := test.URL
	if strings.HasPrefix(urlPath, "http://localhost:5500") {
		urlPath = strings.TrimPrefix(urlPath, "http://localhost:5500/api/")
	} else if strings.HasPrefix(urlPath, "/api/") {
		urlPath = strings.TrimPrefix(urlPath, "/api/")
	}

	// Count warnings, request warnings, and errors from notifications (only in table mode)
	var warnings, requestWarnings, errors int
	if !listMode && result != nil && result.Notifications != nil {
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
												warnings++
											case "request_warning":
												requestWarnings++
											case "error":
												errors++
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

	// Determine pass/fail status (only in table mode)
	status := "\033[32mPASS\033[0m" // Green
	failureReason := ""
	warningCol := ""
	actualStatus := 0

	if !listMode {
		if result == nil {
			// Framework error - must have result in table mode
			status = "\033[1;91mFAIL\033[0m" // Bold bright red
			failureReason = "Framework error: no result"
			warningCol = "  - - -"
		} else {
			actualStatus = result.StatusCode

			// Use comprehensive validation from core
			validation := core.ValidateTest(test.ID, result)

			// Check if status codes match
			statusMatch := actualStatus == test.ExpectedStatus

			// Determine pass/fail using both status check and comprehensive validation
			if !statusMatch {
				status = "\033[1;91mFAIL\033[0m" // Bold bright red
				failureReason = fmt.Sprintf("Expected %d, got %d", test.ExpectedStatus, actualStatus)
			} else if !validation.OK {
				status = "\033[1;91mFAIL\033[0m" // Bold bright red
				if len(validation.Issues) > 0 {
					failureReason = validation.Issues[0] // Show first validation issue
				} else {
					failureReason = "Validation failed"
				}
			} else if errors > 0 {
				status = "\033[1;91mFAIL\033[0m" // Bold bright red
				failureReason = "Validation errors detected"
			}

			// Format W/RW/E column
			warningCol = fmt.Sprintf("%3d %d %d", warnings, requestWarnings, errors)
			if len(result.Data) == 0 {
				warningCol = fmt.Sprintf("  - %d %d", requestWarnings, errors)
			}
		}
	}

	return TableRow{
		ID:            test.ID,
		Category:      test.TestClass,
		URL:           urlPath,
		Method:        test.Method,
		Expected:      test.ExpectedStatus,
		Description:   test.Description,
		Status:        actualStatus,
		WarningCol:    warningCol,
		Pass:          status,
		FailureReason: failureReason,
	}
}

// TableRow represents a row in the test results table
type TableRow struct {
	ID            int
	Category      string
	URL           string
	Method        string
	Expected      int
	Description   string
	Status        int
	WarningCol    string
	Pass          string
	FailureReason string
}

// FormatTable formats multiple test results as a table
func FormatTable(testNumbers []int, results []*core.TestResult) string {
	if len(testNumbers) == 0 {
		return "No test results to display.\n"
	}

	// Get test case definitions
	allTestCases := tests.GetAllTestCases()

	// Determine if we're in list mode (results is nil)
	listMode := results == nil

	var rows []TableRow
	passed := 0
	totalWarnings := 0
	totalRequestWarnings := 0
	totalErrors := 0

	for i, testNum := range testNumbers {
		if testNum < 1 || testNum > len(allTestCases) {
			continue // Skip invalid test numbers
		}

		test := allTestCases[testNum-1]
		var result *core.TestResult
		if !listMode && i < len(results) {
			result = results[i]
		}

		row := FormatTableRow(test, result, listMode)
		rows = append(rows, row)

		if !listMode && strings.Contains(row.Pass, "PASS") {
			passed++
		}

		// Count totals from notifications (only in table mode)
		if !listMode && result != nil && result.Notifications != nil {
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
													totalWarnings++
												case "request_warning":
													totalRequestWarnings++
												case "error":
													totalErrors++
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
	}

	// Build the table
	var result strings.Builder

	if listMode {
		// List mode: [ID, Category, URL, Method, Expected, Description]
		result.WriteString("┌─────┬──────────┬─────────────────────────────────────┬────────┬──────────┬─────────────────────────────────────┐\n")
		result.WriteString("│ ID  │ Category │ URL                                 │ Method │ Expected │ Description                         │\n")
		result.WriteString("├─────┼──────────┼─────────────────────────────────────┼────────┼──────────┼─────────────────────────────────────┤\n")

		// Rows
		for _, row := range rows {
			result.WriteString(fmt.Sprintf("│ %-3d │ %-8s │ %-35s │ %-6s │ %-8d │ %-35s │\n",
				row.ID,
				truncateString(row.Category, 8),
				truncateString(row.URL, 35),
				row.Method,
				row.Expected,
				truncateString(row.Description, 35)))
		}

		// Footer
		result.WriteString("└─────┴──────────┴─────────────────────────────────────┴────────┴──────────┴─────────────────────────────────────┘\n")
	} else {
		// Table mode: [ID, Category, URL, Method, Expected, Description, Actual, W/RW/E, Pass, Failure]
		result.WriteString("┌─────┬──────────┬─────────────────────────────────────┬────────┬──────────┬─────────────────────────────────────┬────────┬─────────┬──────┬──────────────────────────────────────────┐\n")
		result.WriteString("│ ID  │ Category │ URL                                 │ Method │ Expected │ Description                         │ Actual │ W/RW/E  │ Pass │ Failure Reason                           │\n")
		result.WriteString("├─────┼──────────┼─────────────────────────────────────┼────────┼──────────┼─────────────────────────────────────┼────────┼─────────┼──────┼──────────────────────────────────────────┤\n")

		// Rows
		for _, row := range rows {
			result.WriteString(fmt.Sprintf("│ %-3d │ %-8s │ %-35s │ %-6s │ %-8d │ %-35s │ %-6d │ %-7s │ %-4s │ %-40s │\n",
				row.ID,
				truncateString(row.Category, 8),
				truncateString(row.URL, 35),
				row.Method,
				row.Expected,
				truncateString(row.Description, 35),
				row.Status,
				row.WarningCol,
				row.Pass,
				truncateString(row.FailureReason, 40)))
		}

		// Footer
		result.WriteString("└─────┴──────────┴─────────────────────────────────────┴────────┴──────────┴─────────────────────────────────────┴────────┴─────────┴──────┴──────────────────────────────────────────┘\n")

		percentage := float64(passed) / float64(len(rows)) * 100
		result.WriteString(fmt.Sprintf("Summary: %d/%d tests passed (%.1f%%)\n", passed, len(rows), percentage))
	}

	result.WriteString(fmt.Sprintf("Total warnings: %d, Total request warnings: %d, Total errors: %d\n", totalWarnings, totalRequestWarnings, totalErrors))

	return result.String()
}

// truncateString truncates a string to the specified length with ellipsis
func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	if maxLen <= 3 {
		return s[:maxLen]
	}
	return s[:maxLen-3] + "..."
}

// formatWithRawJSON formats raw JSON response while preserving field order
func formatWithRawJSON(rawJSON json.RawMessage, options DisplayOptions, dataLength int) ([]byte, error) {
	// Build jq filter to apply transformations while preserving field order
	filter := "."

	// Apply data truncation if needed
	if !options.ShowAllData && dataLength > 1 {
		filter += " | if .data | type == \"array\" then .data = [.data[0]] else . end"
	}

	// Apply notification truncation if needed
	if !options.ShowNotifications && dataLength > 1 {
		filter += " | if .notifications.warnings then .notifications.warnings = (.notifications.warnings | to_entries | map(.value = (.value | to_entries | .[0:1] | from_entries)) | from_entries) else . end"
	}

	// Use jq to process the JSON while preserving field order
	cmd := exec.Command("jq", "--indent", "2", filter)
	cmd.Stdin = strings.NewReader(string(rawJSON))

	output, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("jq processing failed: %w", err)
	}

	return output, nil
}

// UrlTable displays test information in table format, optionally running tests
func UrlTable(testNumbers []int, runTests bool) string {
	var results []*core.TestResult = nil

	if runTests {
		for _, testNum := range testNumbers {
			result, _ := httpclient.ExecuteTest(testNum)
			results = append(results, result)
		}
	}
	return FormatTable(testNumbers, results)
}
