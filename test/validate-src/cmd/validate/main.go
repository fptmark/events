package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/spf13/cobra"

	"validate/pkg/datagen"
	"validate/pkg/display"
	"validate/pkg/modes"
	"validate/pkg/parser"
	statictestsuite "validate/pkg/static-test-suite"
	"validate/pkg/types"
)

const DefaultServerURL = "http://localhost:5500"

var (
	// Show modes (informational only)
	listMode bool
	testMode bool

	// Run modes (mutually exclusive)
	interactiveMode bool
	writeMode       bool
	summaryMode     bool
	testCategories  string

	// Output expansion (for interactive and write modes)
	showData   bool
	showNotify bool

	// Database reset (always honored)
	resetDB bool

	verbose bool
)

func main() {
	var rootCmd = &cobra.Command{
		Use:   "validate [test-number]",
		Short: "Execute and verify API tests in real-time",
		Long: `Execute and verify API tests in real-time.

Show modes (informational only):
  validate --list             # Show all URLs with test#, category, /api/path
  validate --test             # Show test categories

Run modes (default: table of results):
  validate                    # Run all tests, show table
  validate --interactive      # Interactive verification mode
  validate --summary          # Run all tests, show summary statistics only
  validate 5                  # Run single test, show in table format
  validate --test=basic,sort  # Run filtered tests, show table with gaps

Dump modes (require test#, override run mode):
  validate 5 --data           # Show full data for test 5, then exit
  validate 5 --notify         # Show notifications for test 5, then exit

Database reset (applies to all run modes):
  validate --reset            # Reset database and populate test data before execution`,
		Args: cobra.MaximumNArgs(1),
		Run:  runCommand,
	}

	// Show modes (informational only)
	rootCmd.Flags().BoolVarP(&listMode, "list", "l", false, "Show all URLs with test#, category, /api/path")

	// Combined --test flag that supports both -t (show categories) and --test=categories (run categories)
	rootCmd.Flags().StringVarP(&testCategories, "test", "t", "", "Show test categories or run specific categories (e.g., --test=basic,sort)")
	rootCmd.Flag("test").NoOptDefVal = "show"

	// Run modes (mutually exclusive)
	rootCmd.Flags().BoolVarP(&interactiveMode, "interactive", "i", false, "Interactive verification mode")
	rootCmd.Flags().BoolVarP(&writeMode, "write", "w", false, "Write single test output to stdout and terminate (requires test number)")
	rootCmd.Flags().BoolVarP(&summaryMode, "summary", "s", false, "Show summary statistics only")

	// Output expansion (for interactive and write modes)
	rootCmd.Flags().BoolVarP(&showData, "data", "d", false, "Show full data records")
	rootCmd.Flags().BoolVarP(&showNotify, "notify", "n", false, "Show notification records")

	// Database reset (always honored)
	rootCmd.Flags().BoolVarP(&resetDB, "reset", "r", false, "Reset database and populate test data before execution")
	rootCmd.Flags().BoolVarP(&verbose, "verbose", "v", false, "verbose output (for debugging)")

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runCommand(cmd *cobra.Command, args []string) {
	// Parse test number if provided
	var testID int
	if len(args) > 0 {
		id, err := strconv.Atoi(args[0])
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: Invalid test ID '%s' (must be a number)\n", args[0])
			cmd.Help()
			os.Exit(1)
		}
		testID = id
	}

	// Validate flag combinations and execute appropriate mode
	if err := validateAndExecute(cmd, testID); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %s\n", err)
		cmd.Help()
		os.Exit(1)
	}
}

func validateAndExecute(cmd *cobra.Command, testID int) error {
	datagen.SetConfigDefaults(DefaultServerURL, verbose)

	// Handle show modes first (terminate after showing)
	if listMode {
		modes.ShowURLList()
		return nil
	} else if cmd.Flags().Changed("test") && testCategories == "show" {
		modes.ShowTestCategories()
		return nil
	}

	// Handle database reset if requested (standalone CLI operation)
	if resetDB {
		if err := datagen.ResetAndPopulate(DefaultServerURL, 85, 31); err != nil {
			return fmt.Errorf("database reset failed: %w", err)
		}
	}

	// Get test categories if specified
	var testNums []int
	hasTestCategories := cmd.Flags().Changed("test") && testCategories != "show"

	// Validate test number vs categories
	if testID > 0 && hasTestCategories {
		return fmt.Errorf("cannot combine --test=categories with test number")
	}

	// Get test numbers to run
	if hasTestCategories {
		testNums = getTestNumbers(testCategories)
	} else if testID > 0 {
		testNums = []int{testID}
	} else {
		testNums = getAllTestNumbers()
	}

	// Validate run mode combinations
	runModeCount := 0
	if interactiveMode {
		runModeCount++
	}
	if writeMode {
		runModeCount++
	}
	if summaryMode {
		runModeCount++
	}
	if runModeCount > 1 {
		return fmt.Errorf("only one run mode allowed")
	}

	// Write mode requires test number
	if writeMode && testID == 0 {
		return fmt.Errorf("write mode requires a test number")
	}

	// Initialize HTTP mode for execution
	parser.InitHTTPMode()

	// Execute tests based on mode
	if !resetDB && !writeMode { // display initial record counts if not resetting DB
		initialUsers, initialAccounts, err := datagen.GetRecordCounts(datagen.Config{DefaultServerURL, verbose})
		if err != nil {
			return fmt.Errorf("failed to get initial record counts: %w", err)
		}
		fmt.Printf("Initial records: %d users, %d accounts\n", initialUsers, initialAccounts)
	}
	return runTests(testNums, testID)
}

// Helper functions for the simplified interface

func getTestNumbers(categoriesStr string) []int {
	// Parse categories and return matching test numbers
	categories := strings.Split(categoriesStr, ",")
	for i := range categories {
		categories[i] = strings.TrimSpace(categories[i])
	}

	var testNums []int
	allTests := statictestsuite.GetAllTestCases()

	for i, test := range allTests {
		for _, category := range categories {
			if test.TestClass == category {
				testNums = append(testNums, i+1) // testID is 1-based
				break
			}
		}
	}

	return testNums
}

func getAllTestNumbers() []int {
	allTests := statictestsuite.GetAllTestCases()
	testNums := make([]int, len(allTests))
	for i := range allTests {
		testNums[i] = i + 1 // testID is 1-based
	}
	return testNums
}

// Low-level function that executes a test and returns formatted results
func executeTest(testID int, showAllData, showAllNotify bool) (string, error) {
	// Validate test ID
	totalTests, err := parser.CountTests()
	if err != nil {
		return "", fmt.Errorf("error counting tests: %w", err)
	}
	if testID > totalTests {
		return "", fmt.Errorf("invalid test ID %d (max: %d)", testID, totalTests)
	}

	// Create display options based on flags
	// Default: ShowAllData=false, ShowNotifications=false (truncated data)
	options := display.DisplayOptions{
		ShowAllData:       showAllData,
		ShowNotifications: showAllNotify,
	}

	// Load and execute the test (this does the actual HTTP call)
	testCase, err := parser.LoadTestCase(testID)
	if err != nil {
		return "", fmt.Errorf("error loading test case %d: %v", testID, err)
	}

	// Format the result and return it
	output, err := display.FormatTestResponse(testCase, options)
	if err != nil {
		return "", fmt.Errorf("error formatting response: %v", err)
	}

	return output, nil
}

func runTests(testNums []int, startTestID int) error {
	if writeMode {
		output, err := executeTest(testNums[0], showData, showNotify)
		if err != nil {
			return err
		}
		fmt.Print(output)
		return nil
	} else if interactiveMode {
		return runInteractiveMode(testNums, startTestID)
	} else if summaryMode {
		return runSummaryMode(testNums)
	} else {
		return runTableMode(testNums)
	}
}

func runInteractiveMode(testNums []int, startTestID int) error {
	// Use existing interactive functionality - it already handles data/notify commands
	if startTestID > 0 {
		modes.RunInteractiveVerify(startTestID)
	} else if len(testNums) > 0 {
		modes.RunInteractiveVerify(testNums[0])
	} else {
		modes.RunInteractiveVerify(1)
	}
	return nil
}

func runSummaryMode(testNums []int) error {
	passed := 0
	failed := 0

	for _, testID := range testNums {
		output, err := executeTest(testID, false, false)
		if err != nil {
			failed++
		} else {
			// Check if test passed (simple check for now)
			if strings.Contains(output, "200") {
				passed++
			} else {
				failed++
			}
		}
	}

	fmt.Printf("Summary: %d passed, %d failed, %d total\n", passed, failed, len(testNums))
	return nil
}

func runTableMode(testNums []int) error {
	var testCases []*types.TestCase

	for _, testID := range testNums {
		testCase, err := parser.LoadTestCase(testID)
		if err != nil {
			fmt.Printf("Error loading test %d: %v\n", testID, err)
			continue
		}
		testCases = append(testCases, testCase)
	}

	tableOutput := display.FormatTable(testCases)
	fmt.Print(tableOutput)
	return nil
}
