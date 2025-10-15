package modes

import (
	"fmt"
	"os"

	"validate/pkg/display"
	"validate/pkg/tests"
)

// RunTable runs all tests and displays results in table format
func RunTable(testNumbers []int, showFailuresOnly bool) {
	results, err := tests.ExecuteTests(testNumbers)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	display.ShowTestResults(testNumbers, results, !showFailuresOnly)
	ShowSummary(testNumbers, results)
}
