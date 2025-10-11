package modes

import (
	"fmt"
	"os"

	"validate/pkg/display"
	"validate/pkg/tests"
)

// RunTable runs all tests and displays results in table format
func RunTable(testNumbers []int) {
	results, err := tests.ExecuteTests(testNumbers)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	display.ShowTestResults(testNumbers, results)
	ShowSummary(testNumbers, results)
}
