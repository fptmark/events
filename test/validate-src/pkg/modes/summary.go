package modes

import (
	"fmt"
	"os"

	"validate/pkg/core"
	"validate/pkg/httpclient"
	statictestsuite "validate/pkg/static-test-suite"
)

// RunSummary runs all tests and shows summary statistics
func RunSummary(TestNumbers []int) {
	allCategories := statictestsuite.GetAllCategories()

	for i := 1; i <= len(TestNumbers); i++ {
		testNum := TestNumbers[i-1]
		result, err := httpclient.ExecuteTest(testNum)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error running test %d: %v\n", testNum, err)
			continue
		}

		testCategory := statictestsuite.GetTestCategory(testNum)
		validate := core.ValidateTest(testNum, result)
		if validate.OK {
			allCategories[testCategory].Success++
		} else {
			allCategories[testCategory].Failed++
		}
	}

	// Calculate totals from categories
	var totalSuccess, totalFailure int
	for _, stats := range allCategories {
		totalSuccess += stats.Success
		totalFailure += stats.Failed
	}

	total := totalSuccess + totalFailure
	percentage := float64(totalSuccess) / float64(total) * 100
	fmt.Printf("Summary: %d/%d tests passed (%.1f%%)\n", totalSuccess, total, percentage)

	fmt.Printf("Results by category:\n")
	for category, stats := range allCategories {
		if stats.Success > 0 || stats.Failed > 0 { // Only show categories that were tested
			fmt.Printf("  %s: %d passed, %d failed\n", category, stats.Success, stats.Failed)
		}
	}
}
