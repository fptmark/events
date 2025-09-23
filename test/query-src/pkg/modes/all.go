package modes

import (
	"fmt"
	"os"
	"sort"
	"strings"

	"query-verify/pkg/parser"
	"query-verify/pkg/types"
	"query-verify/pkg/verifier"
)

// TestResult represents the result of a single test verification
type TestResult struct {
	TestID         int
	URL            string
	Description    string
	HTTPStatus     int
	WarningsCount  int
	ErrorsCount    int
	Passed         bool
	FailureReason  string
}

// RunAllMode runs verification on all tests and displays a summary table
func RunAllMode(resultsFile string) {
	// Count total tests
	totalTests, err := parser.CountTests(resultsFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error counting tests: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Running verification on all %d tests...\n\n", totalTests)

	// Initialize verifier
	visualVerifier := verifier.NewVisualVerifier()

	// Collect results for all tests
	var results []TestResult

	for testID := 1; testID <= totalTests; testID++ {
		// Load test case
		testCase, err := parser.LoadTestCase(testID, resultsFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error loading test case %d: %v\n", testID, err)
			continue
		}

		// Extract verification fields
		extraction := parser.ExtractVerificationFields(testCase)

		// Perform verification
		verificationResult := visualVerifier.Verify(testCase, extraction)

		// Count warnings and errors
		warningsCount, errorsCount := countWarningsAndErrors(testCase)

		// Format URL to show path after /api/
		displayURL := formatDisplayURL(testCase.URL)

		// Get failure reason if test failed
		failureReason := ""
		if !verificationResult.Passed && len(verificationResult.Issues) > 0 {
			// Take the first issue as the primary failure reason
			failureReason = verificationResult.Issues[0]
			// Truncate if too long for table display
			if len(failureReason) > 50 {
				failureReason = failureReason[:47] + "..."
			}
		}

		// Create test result
		result := TestResult{
			TestID:        testID,
			URL:           displayURL,
			Description:   testCase.Description,
			HTTPStatus:    testCase.Status,
			WarningsCount: warningsCount,
			ErrorsCount:   errorsCount,
			Passed:        verificationResult.Passed,
			FailureReason: failureReason,
		}

		results = append(results, result)
	}

	// Display summary table
	displaySummaryTable(results)
}

// countWarningsAndErrors counts warnings and errors in the test case response
func countWarningsAndErrors(testCase *types.TestCase) (int, int) {
	warningsCount := 0
	errorsCount := 0

	// The notifications field is interface{}, need to type assert to map
	if notifications, ok := testCase.Result.Notifications.(map[string]interface{}); ok {
		// Count request warnings
		if requestWarnings, ok := notifications["request_warnings"].([]interface{}); ok {
			warningsCount += len(requestWarnings)
		}

		// Count entity warnings
		if warnings, ok := notifications["warnings"].(map[string]interface{}); ok {
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
		if errors, ok := notifications["errors"].(map[string]interface{}); ok {
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

	return warningsCount, errorsCount
}

// formatDisplayURL formats URL to show path after /api/
func formatDisplayURL(url string) string {
	// Find the position of "/api/" and return everything after it
	apiIndex := strings.Index(url, "/api/")
	if apiIndex != -1 {
		return url[apiIndex+5:] // +5 to skip "/api/"
	}
	return url // fallback to full URL if "/api/" not found
}

// displaySummaryTable displays the results in a formatted table
func displaySummaryTable(results []TestResult) {
	// Sort results by test ID
	sort.Slice(results, func(i, j int) bool {
		return results[i].TestID < results[j].TestID
	})

	// Calculate column widths
	maxURLWidth := 30
	maxDescWidth := 35
	maxFailureWidth := 40

	for _, result := range results {
		if len(result.URL) > maxURLWidth {
			maxURLWidth = len(result.URL)
		}
		if len(result.Description) > maxDescWidth {
			maxDescWidth = len(result.Description)
		}
		if len(result.FailureReason) > maxFailureWidth {
			maxFailureWidth = len(result.FailureReason)
		}
	}

	// Limit maximum widths for readability
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
	fmt.Printf("┌─────┬─%s─┬─%s─┬────────┬─────────┬──────┬─%s─┐\n",
		strings.Repeat("─", maxURLWidth),
		strings.Repeat("─", maxDescWidth),
		strings.Repeat("─", maxFailureWidth))

	fmt.Printf("│ %-3s │ %-*s │ %-*s │ %-6s │ %-7s │ %-4s │ %-*s │\n",
		"ID", maxURLWidth, "URL", maxDescWidth, "Description", "Status", "W/E", "Pass", maxFailureWidth, "Failure Reason")

	fmt.Printf("├─────┼─%s─┼─%s─┼────────┼─────────┼──────┼─%s─┤\n",
		strings.Repeat("─", maxURLWidth),
		strings.Repeat("─", maxDescWidth),
		strings.Repeat("─", maxFailureWidth))

	// Print results
	for _, result := range results {
		// Truncate URL, description, and failure reason if needed
		displayURL := result.URL
		if len(displayURL) > maxURLWidth {
			displayURL = displayURL[:maxURLWidth-3] + "..."
		}

		displayDesc := result.Description
		if len(displayDesc) > maxDescWidth {
			displayDesc = displayDesc[:maxDescWidth-3] + "..."
		}

		displayFailure := result.FailureReason
		if len(displayFailure) > maxFailureWidth {
			displayFailure = displayFailure[:maxFailureWidth-3] + "..."
		}

		// Format pass/fail with color
		passStatus := "\033[31mFAIL\033[0m" // Red for FAIL
		if result.Passed {
			passStatus = "\033[32mPASS\033[0m" // Green for PASS
		}

		// Format warnings/errors with fixed width (5 characters: "XX YY")
		warnErrStr := fmt.Sprintf("%2d %2d", result.WarningsCount, result.ErrorsCount)

		fmt.Printf("│ %-3d │ %-*s │ %-*s │ %-6d │ %-7s │ %-4s │ %-*s │\n",
			result.TestID,
			maxURLWidth, displayURL,
			maxDescWidth, displayDesc,
			result.HTTPStatus,
			warnErrStr,
			passStatus,
			maxFailureWidth, displayFailure)
	}

	// Print footer
	fmt.Printf("└─────┴─%s─┴─%s─┴────────┴─────────┴──────┴─%s─┘\n",
		strings.Repeat("─", maxURLWidth),
		strings.Repeat("─", maxDescWidth),
		strings.Repeat("─", maxFailureWidth))

	// Print summary statistics
	totalTests := len(results)
	passedTests := 0
	totalWarnings := 0
	totalErrors := 0

	for _, result := range results {
		if result.Passed {
			passedTests++
		}
		totalWarnings += result.WarningsCount
		totalErrors += result.ErrorsCount
	}

	fmt.Printf("\n")
	fmt.Printf("Summary: %d/%d tests passed (%.1f%%)\n",
		passedTests, totalTests, float64(passedTests)/float64(totalTests)*100)
	fmt.Printf("Total warnings: %d, Total errors: %d\n", totalWarnings, totalErrors)
}