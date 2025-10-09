package modes

import (
	"fmt"
	"os"
	"sort"

	"validate/pkg/core"
	"validate/pkg/tests"
	"validate/pkg/types"
)

// RunSummary runs all tests and shows summary statistics
func RunSummary(testNums []int) {
	results, err := core.ExecuteTests(testNums)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	ShowSummary(testNums, results)
}

func ShowSummary(testNumbers []int, results []*types.TestResult) {
	allTests := tests.GetAllTestCases()
	categoryStats := tests.GetAllCategories()

	for i, result := range results {
		if result == nil {
			continue
		}
		testNum := testNumbers[i]
		testCase := allTests[testNum-1]
		category := testCase.TestClass

		if result.Passed {
			categoryStats[category].Success++
		} else {
			categoryStats[category].Failed++
		}
	}

	var totalSuccess, totalFailure int
	for _, stats := range categoryStats {
		totalSuccess += stats.Success
		totalFailure += stats.Failed
	}

	total := totalSuccess + totalFailure
	percentage := float64(totalSuccess) / float64(total) * 100
	fmt.Printf("Summary: %d/%d/%d tests passed/failed/total (%.1f%%)\n", totalSuccess, totalFailure, total, percentage)

	fmt.Printf("Results by category:\n")

	// Sort categories alphabetically for consistent output
	var categories []string
	for category := range categoryStats {
		categories = append(categories, category)
	}
	sort.Strings(categories)

	for _, category := range categories {
		stats := categoryStats[category]
		if stats.Success > 0 || stats.Failed > 0 {
			out := fmt.Sprintf("  %s: %d passed, %d failed\n", category, stats.Success, stats.Failed)
			if stats.Failed == 0 {
				fmt.Printf("\033[32m%s\033[0m", out)
			} else {
				fmt.Printf("\033[1;91m%s\033[0m", out)
			}
		}
	}
}
