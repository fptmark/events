package modes

import (
	"fmt"
	"os"
	"strings"

	"validate/pkg/core"
	"validate/pkg/parser"
)

// TableRow represents a row in the test results table
type TableRow struct {
	ID            int
	URL           string
	Description   string
	Category      string
	Status        int
	WarningsCount int
	RequestWarningsCount int
	ErrorsCount   int
	Passed        bool
	FailureReason string
}

// RunTable runs all tests and displays results in table format
func RunTable() {
	totalTests, err := parser.CountTests()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error counting tests: %v\n", err)
		os.Exit(1)
	}

	var rows []TableRow
	for testNum := 1; testNum <= totalTests; testNum++ {
		result, err := core.RunTest(testNum)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error running test %d: %v\n", testNum, err)
			continue
		}

		validate := core.ValidateTest(testNum, result)

		// Count warnings and errors
		warningsCount, requestWarningsCount, errorsCount := countNotifications(result.Notifications)

		// Format URL to show path after /api/
		displayURL := formatDisplayURL(result.URL)

		// Get failure reason
		failureReason := ""
		if !validate.OK && len(validate.Issues) > 0 {
			failureReason = validate.Issues[0]
			if len(failureReason) > 40 {
				failureReason = failureReason[:37] + "..."
			}
		}

		row := TableRow{
			ID:                   result.ID,
			URL:                  displayURL,
			Description:          result.Description,
			Category:             result.TestClass,
			Status:               result.StatusCode,
			WarningsCount:        warningsCount,
			RequestWarningsCount: requestWarningsCount,
			ErrorsCount:          errorsCount,
			Passed:               validate.OK,
			FailureReason:        failureReason,
		}
		rows = append(rows, row)
	}

	displayTable(rows)
}

// countNotifications counts warnings, request warnings, and errors
func countNotifications(notifications interface{}) (int, int, int) {
	warningsCount := 0
	requestWarningsCount := 0
	errorsCount := 0

	if notifications == nil {
		return warningsCount, requestWarningsCount, errorsCount
	}

	if notifMap, ok := notifications.(map[string]interface{}); ok {
		// Count request warnings
		if requestWarnings, ok := notifMap["request_warnings"].([]interface{}); ok {
			requestWarningsCount = len(requestWarnings)
		}

		// Count entity warnings
		if warnings, ok := notifMap["warnings"].(map[string]interface{}); ok {
			for _, entityMap := range warnings {
				if entityWarnings, ok := entityMap.(map[string]interface{}); ok {
					for _, instanceList := range entityWarnings {
						if instanceWarnings, ok := instanceList.([]interface{}); ok {
							warningsCount += len(instanceWarnings)
						}
					}
				}
			}
		}

		// Count entity errors
		if errors, ok := notifMap["errors"].(map[string]interface{}); ok {
			for _, entityMap := range errors {
				if entityErrors, ok := entityMap.(map[string]interface{}); ok {
					for _, instanceList := range entityErrors {
						if instanceErrors, ok := instanceList.([]interface{}); ok {
							errorsCount += len(instanceErrors)
						}
					}
				}
			}
		}
	}

	return warningsCount, requestWarningsCount, errorsCount
}

// formatDisplayURL formats URL to show path after /api/
func formatDisplayURL(url string) string {
	apiIndex := strings.Index(url, "/api/")
	if apiIndex != -1 {
		return url[apiIndex+5:] // +5 to skip "/api/"
	}
	return url
}

// displayTable formats and displays the table
func displayTable(rows []TableRow) {
	if len(rows) == 0 {
		fmt.Println("No test results to display.")
		return
	}

	// Calculate column widths
	maxURLWidth := 30
	maxDescWidth := 35
	maxFailureWidth := 40

	for _, row := range rows {
		if len(row.URL) > maxURLWidth {
			maxURLWidth = len(row.URL)
		}
		if len(row.Description) > maxDescWidth {
			maxDescWidth = len(row.Description)
		}
		if len(row.FailureReason) > maxFailureWidth {
			maxFailureWidth = len(row.FailureReason)
		}
	}

	// Limit maximum widths
	if maxURLWidth > 60 {
		maxURLWidth = 60
	}
	if maxDescWidth > 35 {
		maxDescWidth = 35
	}
	if maxFailureWidth > 40 {
		maxFailureWidth = 40
	}

	// Print header
	fmt.Printf("┌─────┬─%s─┬─%s─┬──────────┬────────┬─────────┬──────┬─%s─┐\n",
		strings.Repeat("─", maxURLWidth),
		strings.Repeat("─", maxDescWidth),
		strings.Repeat("─", maxFailureWidth))

	fmt.Printf("│ %-3s │ %-*s │ %-*s │ %-8s │ %-6s │ %-7s │ %-4s │ %-*s │\n",
		"ID", maxURLWidth, "URL", maxDescWidth, "Description", "Category", "Status", "W/RW/E", "Pass", maxFailureWidth, "Failure Reason")

	fmt.Printf("├─────┼─%s─┼─%s─┼──────────┼────────┼─────────┼──────┼─%s─┤\n",
		strings.Repeat("─", maxURLWidth),
		strings.Repeat("─", maxDescWidth),
		strings.Repeat("─", maxFailureWidth))

	// Print rows
	passed := 0
	totalWarnings := 0
	totalRequestWarnings := 0
	totalErrors := 0

	for _, row := range rows {
		// Truncate strings if needed
		displayURL := row.URL
		if len(displayURL) > maxURLWidth {
			displayURL = displayURL[:maxURLWidth-3] + "..."
		}

		displayDesc := row.Description
		if len(displayDesc) > maxDescWidth {
			displayDesc = displayDesc[:maxDescWidth-3] + "..."
		}

		displayFailure := row.FailureReason
		if len(displayFailure) > maxFailureWidth {
			displayFailure = displayFailure[:maxFailureWidth-3] + "..."
		}

		// Format pass/fail with color
		passStatus := "\033[31mFAIL\033[0m" // Red
		if row.Passed {
			passStatus = "\033[32mPASS\033[0m" // Green
			passed++
		}

		// Format warnings/request warnings/errors
		wStr := "-"
		if row.WarningsCount > 0 {
			wStr = fmt.Sprintf("%d", row.WarningsCount)
		}

		rwStr := "-"
		if row.RequestWarningsCount > 0 {
			rwStr = fmt.Sprintf("%d", row.RequestWarningsCount)
		}

		eStr := "-"
		if row.ErrorsCount > 0 {
			eStr = fmt.Sprintf("%d", row.ErrorsCount)
		}

		warnErrStr := fmt.Sprintf("%3s %s %s", wStr, rwStr, eStr)

		fmt.Printf("│ %-3d │ %-*s │ %-*s │ %-8s │ %-6d │ %-7s │ %-4s │ %-*s │\n",
			row.ID,
			maxURLWidth, displayURL,
			maxDescWidth, displayDesc,
			row.Category,
			row.Status,
			warnErrStr,
			passStatus,
			maxFailureWidth, displayFailure)

		// Update totals
		totalWarnings += row.WarningsCount
		totalRequestWarnings += row.RequestWarningsCount
		totalErrors += row.ErrorsCount
	}

	// Print footer
	fmt.Printf("└─────┴─%s─┴─%s─┴──────────┴────────┴─────────┴──────┴─%s─┘\n",
		strings.Repeat("─", maxURLWidth),
		strings.Repeat("─", maxDescWidth),
		strings.Repeat("─", maxFailureWidth))

	// Print summary
	total := len(rows)
	percentage := float64(passed) / float64(total) * 100
	fmt.Printf("Summary: %d/%d tests passed (%.1f%%)\n", passed, total, percentage)
	fmt.Printf("Total warnings: %d, Total request warnings: %d, Total errors: %d\n",
		totalWarnings, totalRequestWarnings, totalErrors)
}