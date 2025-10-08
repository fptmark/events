package modes

import (
	"encoding/json"
	"fmt"
	"strings"

	"validate/pkg/types"
)

// formatResult formats a test case and its result for display
func formatResult(testCase *types.TestCase, result *types.TestResult, showData bool, showNotify bool) string {
	var output strings.Builder

	// Show test metadata
	output.WriteString(fmt.Sprintf("Test #%d: %s %s\n", testCase.ID, testCase.Method, testCase.URL))
	if testCase.Description != "" {
		output.WriteString(fmt.Sprintf("Description: %s\n", testCase.Description))
	}
	output.WriteString(fmt.Sprintf("HTTP Status: %d\n\n", result.StatusCode))

	output.WriteString("Response:\n")

	dataLength := len(result.Data)
	suppressNotifications := !showNotify && dataLength > 1

	// Build display data
	displayData := result.Data
	if !showData && dataLength > 1 {
		displayData = result.Data[:1]
		output.WriteString(fmt.Sprintf("  (Showing first record only, use --data to see all %d records)\n", dataLength))
	}

	// Build display notifications
	displayNotifications := result.Notifications
	if suppressNotifications {
		displayNotifications = nil
		output.WriteString("  (Notifications suppressed for multi-record response, use --notify to see them)\n")
	}

	// Marshal to JSON for display
	response := map[string]interface{}{
		"data":          displayData,
		"notifications": displayNotifications,
		"status":        fmt.Sprintf("%d", result.StatusCode),
	}

	jsonBytes, err := json.MarshalIndent(response, "", "  ")
	if err != nil {
		return fmt.Sprintf("Error formatting response: %v\n", err)
	}

	output.WriteString(string(jsonBytes))
	output.WriteString("\n\n")

	// Show pass/fail status in color at the bottom
	if result.Passed {
		output.WriteString("\033[32mPASS\033[0m\n")
	} else {
		output.WriteString("\033[1;91mFAIL\033[0m\n")
	}

	return output.String()
}
