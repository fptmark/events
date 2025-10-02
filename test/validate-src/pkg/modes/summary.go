package modes

import (
	"fmt"
	"os"

	"validate/pkg/core"
	"validate/pkg/parser"
)

// RunSummary runs all tests and shows summary statistics
func RunSummary() {
	totalTests, err := parser.CountTests()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error counting tests: %v\n", err)
		os.Exit(1)
	}

	success := 0
	failure := 0

	for testNum := 1; testNum <= totalTests; testNum++ {
		result, err := core.RunTest(testNum)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error running test %d: %v\n", testNum, err)
			continue
		}

		validate := core.ValidateTest(testNum, result)
		if validate.OK {
			success++
		} else {
			failure++
		}
	}

	total := success + failure
	percentage := float64(success) / float64(total) * 100
	fmt.Printf("Summary: %d/%d tests passed (%.1f%%)\n", success, total, percentage)
}