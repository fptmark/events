package modes

import (
	"fmt"
	"os"

	"validate/pkg/display"
	"validate/pkg/parser"
)

// RunSummaryMode displays a test summary with optional data/notification flags
func RunSummaryMode(testID int, options display.DisplayOptions) {
	// Load the test case
	testCase, err := parser.LoadTestCase(testID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading test case %d: %v\n", testID, err)

		// Fall back to list mode on error (matching bash script behavior)
		fmt.Println()
		RunListMode()
		os.Exit(1)
	}

	// Format and display the response
	output, err := display.FormatTestResponse(testCase, options)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error formatting response: %v\n", err)
		os.Exit(1)
	}

	fmt.Print(output)
}