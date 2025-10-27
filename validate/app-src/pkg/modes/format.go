package modes

import (
	"bytes"
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

	// Show HTTP Status with expected vs actual and pass/fail indicator
	statusLine := fmt.Sprintf("HTTP Status: Expected=%d  Response=%d ", testCase.ExpectedStatus, result.StatusCode)
	if result.Passed {
		statusLine += "\033[32mPASS\033[0m"
	} else if result.Alert {
		statusLine += "\033[33mALERT\033[0m"
	} else {
		statusLine += "\033[1;91mFAIL\033[0m"
	}
	output.WriteString(statusLine + "\n")

	// Validation already done in executor.ExecuteTests() - no need to call again here

	// Show validation issues if test failed
	if !result.Passed && len(result.Issues) > 0 {
		output.WriteString("Issues:\n")
		for _, issue := range result.Issues {
			output.WriteString(fmt.Sprintf("  - %s\n", issue))
		}
	}

	// Show informational notes if present (even if test passed)
	if len(result.Notes) > 0 {
		output.WriteString("Notes:\n")
		for _, note := range result.Notes {
			output.WriteString(fmt.Sprintf("  - %s\n", note))
		}
	}

	// Show RequestBody for POST/PUT tests
	if (testCase.Method == "POST" || testCase.Method == "PUT") && testCase.RequestBody != nil {
		output.WriteString("\nRequest Body:\n")
		requestJSON, err := json.MarshalIndent(testCase.RequestBody, "  ", "  ")
		if err == nil {
			output.WriteString("  ")
			output.WriteString(string(requestJSON))
			output.WriteString("\n")
		}
	}
	output.WriteString("\n")

	output.WriteString("Response:\n")

	dataLength := len(result.Data)

	// If we need to truncate or suppress, we have to re-marshal (and lose ordering)
	// Otherwise, use raw response to preserve server's field ordering
	if (!showData && dataLength > 1) || (!showNotify && dataLength > 1) {
		// Need to modify response - build custom version
		suppressNotifications := !showNotify && dataLength > 1

		displayData := result.Data
		if !showData && dataLength > 1 {
			displayData = result.Data[:1]
			output.WriteString(fmt.Sprintf("  (Showing first record only, use --data to see all %d records)\n", dataLength))
		}

		displayNotifications := result.Notifications
		if suppressNotifications {
			displayNotifications = nil
			output.WriteString("  (Notifications suppressed for multi-record response, use --notify to see them)\n")
		}

		// Marshal to JSON for display (field order will be alphabetic)
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
	} else {
		// Use raw response body to preserve server's field ordering
		var prettyJSON bytes.Buffer
		if err := json.Indent(&prettyJSON, result.RawResponseBody, "", "  "); err != nil {
			// Not JSON - likely HTML, show first 10 lines
			output.WriteString("(Non-JSON response - showing first 10 lines)\n")
			lines := strings.Split(string(result.RawResponseBody), "\n")
			if len(lines) > 10 {
				lines = lines[:10]
			}
			output.WriteString(strings.Join(lines, "\n"))
			output.WriteString("\n")
		} else {
			output.WriteString(prettyJSON.String())
		}
	}

	output.WriteString("\n\n")

	// Show sort and filter field values (validation already called above)
	if len(result.Fields) > 0 {
		output.WriteString("Field Values:\n")
		for fieldKey, values := range result.Fields {
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
