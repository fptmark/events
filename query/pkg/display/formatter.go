package display

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"

	"query-verify/pkg/types"
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

	// Format the JSON response
	jsonBytes, err := json.MarshalIndent(map[string]interface{}{
		"data":          displayResult.Data,
		"notifications": notificationsForDisplay,
		"status":        displayResult.Status,
	}, "", "  ")
	if err != nil {
		return "", fmt.Errorf("error formatting JSON: %w", err)
	}

	result.WriteString(string(jsonBytes))
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