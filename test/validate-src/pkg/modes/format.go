package modes

import (
	"encoding/json"
	"fmt"
	"strings"

	"validate/pkg/tests"
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

	// Show sort and filter field values (before pass/fail status)
	validation := tests.ValidateTest(testCase.ID, result)
	if len(validation.Fields) > 0 {
		output.WriteString("Field Values:\n")
		for fieldKey, values := range validation.Fields {
			// Skip view parameter fields
			if strings.HasPrefix(fieldKey, "view_") {
				continue
			}

			// Limit to 10 values
			displayValues := values
			if len(values) > 10 {
				displayValues = values[:10]
			}

			// Format values for display
			formattedValues := make([]string, len(displayValues))
			for i, val := range displayValues {
				formattedValues[i] = formatValue(val)
			}

			output.WriteString(fmt.Sprintf("%s = [%s]\n", fieldKey, strings.Join(formattedValues, ", ")))
		}
		output.WriteString("\n")
	}

	// Show pass/fail/alert status in color at the bottom
	if result.Passed {
		output.WriteString("\033[32mPASS\033[0m\n")
	} else if result.Alert {
		output.WriteString("\033[33mALERT: Record already exists (run with --reset or delete manually)\033[0m\n")
	} else {
		output.WriteString("\033[1;91mFAIL\033[0m\n")
	}

	return output.String()
}

// formatValue formats a value for display with proper number formatting
func formatValue(val interface{}) string {
	switch v := val.(type) {
	case float64:
		if v < 1000 {
			// Show decimals for values under 1000
			return fmt.Sprintf("%.2f", v)
		}
		// For values >= 1000, format with commas and strip decimal if it's .00
		formatted := formatFloatWithCommas(v)
		return formatted
	case int:
		return formatNumberWithCommas(int64(v))
	case int64:
		return formatNumberWithCommas(v)
	case string:
		return v
	default:
		return fmt.Sprintf("%v", v)
	}
}

// formatFloatWithCommas formats a float with comma separators (no decimals for values >= 1000)
func formatFloatWithCommas(f float64) string {
	// Just format the integer part with commas
	intPart := int64(f)
	return formatNumberWithCommas(intPart)
}

// formatNumberWithCommas formats an integer with comma separators
func formatNumberWithCommas(n int64) string {
	if n < 0 {
		return "-" + formatNumberWithCommas(-n)
	}
	if n < 1000 {
		return fmt.Sprintf("%d", n)
	}
	return formatNumberWithCommas(n/1000) + "," + fmt.Sprintf("%03d", n%1000)
}
