package display

import (
	"fmt"
	"strings"

	"validate/pkg/tests"
	"validate/pkg/types"
)

// FormatTableRow formats a single test result as a table row
func FormatTableRow(test types.TestCase, result *types.TestResult) TableRow {
	// Determine pass/fail status
	status := "\033[32mPASS\033[0m" // Green
	notes := ""
	warningCol := ""
	actualStatus := 0
	warnings := 0
	requestWarnings := 0
	errors := 0

	if result == nil {
		// Framework error - must have result in table mode
		status = "\033[1;91mFAIL\033[0m" // Bold bright red
		notes = "Framework error: no result"
		warningCol = "  - - -"
	} else {
		actualStatus = result.StatusCode
		warnings = result.Warnings
		requestWarnings = result.RequestWarnings
		errors = result.Errors

		// Use result.Passed which was calculated in core.ExecuteTests
		if result.Passed {
			status = "\033[32mPASS\033[0m"
			// For passing tests, show notes from validation (e.g., "MongoDB fuzzy match")
			if len(result.Notes) > 0 {
				notes = strings.Join(result.Notes, "; ")
			}
		} else {
			status = "\033[1;91mFAIL\033[0m" // Bold bright red

			// For failing tests, show failure reason
			if result.StatusCode != test.ExpectedStatus {
				notes = fmt.Sprintf("Expected %d, got %d", test.ExpectedStatus, result.StatusCode)
			} else if errors > 0 {
				notes = "Validation errors detected"
			} else {
				notes = "Validation failed"
			}
		}

		// Format W/RW/E column
		warningCol = fmt.Sprintf("%3d %d %d", warnings, requestWarnings, errors)
		if len(result.Data) == 0 {
			warningCol = fmt.Sprintf("  - %d %d", requestWarnings, errors)
		}
	}

	return TableRow{
		TestCase:        test,
		Status:          actualStatus,
		WarningCol:      warningCol,
		Pass:            status,
		Notes:           notes,
		Warnings:        warnings,
		RequestWarnings: requestWarnings,
		Errors:          errors,
	}
}

// TableRow represents a row in the test results table
type TableRow struct {
	TestCase        types.TestCase
	Status          int
	WarningCol      string
	Pass            string
	Notes           string
	Warnings        int
	RequestWarnings int
	Errors          int
}

func ListTests(testNumbers []int) {
	// List mode: [ID, Category, URL, Method, Expected, Description]
	fmt.Print("┌─────┬──────────┬─────────────────────────────────────┬────────┬──────────┬─────────────────────────────────────┐\n")
	fmt.Print("│ ID  │ Category │ URL                                 │ Method │ Expected │ Description                         │\n")
	fmt.Print("├─────┼──────────┼─────────────────────────────────────┼────────┼──────────┼─────────────────────────────────────┤\n")

	// Rows
	for _, row := range tests.GetAllTestCases() {
		fmt.Printf("│ %-3d │ %-8s │ %-35s │ %-6s │ %-8d │ %-35s │\n",
			row.ID,
			truncateString(row.TestClass, 8),
			truncateString(row.URL, 35),
			row.Method,
			row.ExpectedStatus,
			truncateString(row.Description, 35))
	}

	// Footer
	fmt.Print("└─────┴──────────┴─────────────────────────────────────┴────────┴──────────┴─────────────────────────────────────┘\n")
}

// ShowTestResults displays multiple test results as a table
func ShowTestResults(testNumbers []int, results []*types.TestResult, showAll bool) {
	if len(testNumbers) == 0 {
		fmt.Print("No test results to display.\n")
		return
	}

	// Get test case definitions
	allTestCases := tests.GetAllTestCases()

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
		var result *types.TestResult
		if i < len(results) {
			result = results[i]
		}

		row := FormatTableRow(test, result)
		rows = append(rows, row)

		if strings.Contains(row.Pass, "PASS") {
			passed++
		}

		totalWarnings += row.Warnings
		totalRequestWarnings += row.RequestWarnings
		totalErrors += row.Errors
	}

	// Build the table
	fmt.Print("┌─────┬──────────┬─────────────────────────────────────┬────────┬──────────┬─────────────────────────────────────┬────────┬─────────┬──────┬──────────────────────────────────────────┐\n")
	fmt.Print("│ ID  │ Category │ URL                                 │ Method │ Expected │ Description                         │ Actual │ W/RW/E  │ Pass │ Notes                                    │\n")
	fmt.Print("├─────┼──────────┼─────────────────────────────────────┼────────┼──────────┼─────────────────────────────────────┼────────┼─────────┼──────┼──────────────────────────────────────────┤\n")

	// Rows
	for _, row := range rows {
		urlPath := row.TestCase.URL
		if strings.HasPrefix(urlPath, "http://localhost:5500") {
			urlPath = strings.TrimPrefix(urlPath, "http://localhost:5500/api/")
		} else if strings.HasPrefix(urlPath, "/api/") {
			urlPath = strings.TrimPrefix(urlPath, "/api/")
		}

		if showAll || strings.Contains(row.Pass, "FAIL") {
			fmt.Printf("│ %-3d │ %-8s │ %-35s │ %-6s │ %-8d │ %-35s │ %-6d │ %-7s │ %-4s │ %-40s │\n",
				row.TestCase.ID,
				truncateString(row.TestCase.TestClass, 8),
				truncateString(urlPath, 35),
				row.TestCase.Method,
				row.TestCase.ExpectedStatus,
				truncateString(row.TestCase.Description, 35),
				row.Status,
				row.WarningCol,
				row.Pass,
				truncateString(row.Notes, 40))
		}
	}

	// Footer
	fmt.Print("└─────┴──────────┴─────────────────────────────────────┴────────┴──────────┴─────────────────────────────────────┴────────┴─────────┴──────┴──────────────────────────────────────────┘\n")

	fmt.Printf("Total warnings: %d, Total request warnings: %d, Total errors: %d\n", totalWarnings, totalRequestWarnings, totalErrors)
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
