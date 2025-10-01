package modes

import (
	"fmt"
	"os"
	"strings"

	"validate/pkg/display"
	"validate/pkg/parser"
	statictestsuite "validate/pkg/static-test-suite"
)

// executeAndDisplayTest loads and displays a single test with the given options
func executeAndDisplayTest(testID int, options display.DisplayOptions) {
	// Load the test case
	testCase, err := parser.LoadTestCase(testID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading test case %d: %v\n", testID, err)
		os.Exit(1)
	}

	// Display the result with specified options
	output, err := display.FormatTestResponse(testCase, options)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error formatting response: %v\n", err)
		os.Exit(1)
	}

	fmt.Print(output)
}

// RunSingleTest executes a single test and displays it in table format
func RunSingleTest(testID int) {
	options := display.DisplayOptions{
		ShowAllData:       false,
		ShowNotifications: false,
	}
	executeAndDisplayTest(testID, options)
}

// RunTestsByCategory executes tests filtered by categories, showing table with gaps
func RunTestsByCategory(categoriesStr string) {
	// Parse requested categories
	categories := strings.Split(categoriesStr, ",")
	for i := range categories {
		categories[i] = strings.TrimSpace(categories[i])
	}

	fmt.Printf("Running tests for categories: %s\n", strings.Join(categories, ", "))
	fmt.Println("=" + strings.Repeat("=", 50))

	// Get matching test IDs while preserving original numbering
	allTests := statictestsuite.GetAllTestCases()
	matchingTests := make(map[int]bool)

	for i, test := range allTests {
		for _, category := range categories {
			if test.TestClass == category {
				matchingTests[i+1] = true // testID is 1-based
				break
			}
		}
	}

	if len(matchingTests) == 0 {
		fmt.Printf("No tests found for categories: %s\n", strings.Join(categories, ", "))
		return
	}

	// Run only matching tests but maintain original test numbers
	fmt.Printf("Found %d matching tests\n\n", len(matchingTests))

	for testID := 1; testID <= len(allTests); testID++ {
		if matchingTests[testID] {
			fmt.Printf("=== Test %d ===\n", testID)
			RunSingleTest(testID)
			fmt.Println()
		}
	}
}

// RunAllTestsWithTable executes all tests and displays them in table format
func RunAllTestsWithTable() {
	// Use existing RunAllMode functionality
	RunAllMode()
}

// RunAllTestsStatsOnly executes all tests and shows only summary statistics
func RunAllTestsStatsOnly() {
	// Use existing RunSummaryOnlyMode functionality
	RunSummaryOnlyMode()
}

// RunInteractiveVerify runs tests in interactive verification mode
func RunInteractiveVerify(testID int) {
	// Use existing RunVerifyMode functionality
	RunVerifyMode(testID)
}

// DumpTestData shows full data for a specific test, then exits
func DumpTestData(testID int) {
	options := display.DisplayOptions{
		ShowAllData:       true,
		ShowNotifications: false,
	}
	executeAndDisplayTest(testID, options)
}

// DumpTestNotifications shows notifications for a specific test, then exits
func DumpTestNotifications(testID int) {
	options := display.DisplayOptions{
		ShowAllData:       false,
		ShowNotifications: true,
	}
	executeAndDisplayTest(testID, options)
}