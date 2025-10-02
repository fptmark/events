package modes

import (
	"encoding/json"
	"fmt"
	"os"

	"validate/pkg/core"
)

// RunWrite runs a single test and outputs formatted result
func RunWrite(testNum int, fullData bool, fullNotifications bool) {
	result, err := core.RunTest(testNum)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error running test %d: %v\n", testNum, err)
		os.Exit(1)
	}

	// Format and display the result
	displayData := result.Data
	displayNotifications := result.Notifications

	// Apply data filtering
	if !fullData && len(result.Data) > 1 {
		displayData = result.Data[:1]
		fmt.Printf("  (Showing first record only, use --data to see all %d records)\n", len(result.Data))
	}

	// Apply notification filtering
	if !fullNotifications && len(result.Data) > 1 {
		displayNotifications = truncateNotifications(result.Notifications, result.Data)
		fmt.Printf("  (Warnings truncated to first entity ID per type, use --notify to show all)\n")
	}

	// Create JSON response
	response := map[string]interface{}{
		"data":          displayData,
		"notifications": displayNotifications,
		"status":        result.Status,
	}

	jsonBytes, err := json.MarshalIndent(response, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error formatting JSON: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("Response:")
	fmt.Println(string(jsonBytes))
	fmt.Printf("\nURL: %s\n", result.URL)
	fmt.Printf("Status: %s\n", result.Status)
}

// truncateNotifications truncates notifications to first entity per type
func truncateNotifications(notifications interface{}, data []map[string]interface{}) interface{} {
	if notifications == nil {
		return nil
	}

	// Get entity ID from first data record if available
	var entityID string
	if len(data) > 0 && data[0] != nil {
		if id, ok := data[0]["id"].(string); ok {
			entityID = id
		}
	}

	if notifMap, ok := notifications.(map[string]interface{}); ok {
		if warnings, ok := notifMap["warnings"].(map[string]interface{}); ok {
			truncatedWarnings := make(map[string]interface{})

			for entityType, entityMap := range warnings {
				if entityWarnings, ok := entityMap.(map[string]interface{}); ok {
					truncatedEntityMap := make(map[string]interface{})

					if entityID != "" {
						// Use specific entity ID if available
						if errors, exists := entityWarnings[entityID]; exists {
							truncatedEntityMap[entityID] = errors
						}
					} else {
						// Fallback: keep only the first entity ID
						for eID, errors := range entityWarnings {
							truncatedEntityMap[eID] = errors
							break
						}
					}

					if len(truncatedEntityMap) > 0 {
						truncatedWarnings[entityType] = truncatedEntityMap
					}
				}
			}

			return map[string]interface{}{
				"warnings": truncatedWarnings,
			}
		}
	}

	return notifications
}