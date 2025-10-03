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
	"validate/pkg/tests"
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
			os.Exit(1)
		}
		testID = id
	}

	// Validate flag combinations and execute appropriate mode
	if err := validateAndExecute(cmd, testID); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %s\n", err)
		os.Exit(1)
	}
}

func validateAndExecute(cmd *cobra.Command, testID int) error {
	datagen.SetConfigDefaults(DefaultServerURL, verbose)

	// Get test categories if specified
	var testNums []int
	hasTestCategories := cmd.Flags().Changed("test") && testCategories != "show"

	// Validate test number vs categories
	if testID > 0 && hasTestCategories {
		return fmt.Errorf("cannot combine --test=categories with test number")
	}

	// Get test numbers to run FIRST (before any mode handling)
	if hasTestCategories {
		testNums = getTestNumbers(testCategories)
	} else if testID > 0 {
		testNums = []int{testID}
	} else {
		testNums = getAllTestNumbers()
	}

	// Validate all test numbers ONCE here
	if err := validateTestNumbers(testNums); err != nil {
		return err
	}

	// Handle show modes (now with filtered testNums)
	if listMode {
		output := display.UrlTable(testNums, false) // Use filtered testNums
		fmt.Print(output)
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

	// Auto-enable write mode if data/notify flags are used
	if (showData || showNotify) && !writeMode {
		writeMode = true
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

	// Write mode (including data/notify modes) requires test number
	if writeMode && testID == 0 {
		return fmt.Errorf("write mode requires a test number")
	}


	// Execute tests based on mode
	if !resetDB && !(writeMode || showData || showNotify) { // display initial record counts if not resetting DB or in single-output modes
		initialUsers, initialAccounts, err := datagen.GetRecordCounts(datagen.Config{DefaultServerURL, verbose})
		if err != nil {
			return fmt.Errorf("failed to get initial record counts: %w", err)
		}
		fmt.Printf("Initial records: %d users, %d accounts\n", initialUsers, initialAccounts)
	}

	return runTests(testNums, testID)
}

// validateTestNumbers checks that all test numbers are in valid range
func validateTestNumbers(testNumbers []int) error {
	allTests := tests.GetAllTestCases()
	totalTests := len(allTests)
	for _, testNum := range testNumbers {
		if testNum < 1 || testNum > totalTests {
			return fmt.Errorf("test ID %d out of range (1-%d)", testNum, totalTests)
		}
	}
	return nil
}

// Helper functions for the simplified interface

func getTestNumbers(categoriesStr string) []int {
	// Parse categories and return matching test numbers
	categories := strings.Split(categoriesStr, ",")
	for i := range categories {
		categories[i] = strings.TrimSpace(categories[i])
	}

	var testNums []int
	allTests := tests.GetAllTestCases()

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
	allTests := tests.GetAllTestCases()
	testNums := make([]int, len(allTests))
	for i := range allTests {
		testNums[i] = i + 1 // testID is 1-based
	}
	return testNums
}


func runTests(testNums []int, startTestID int) error {
	if writeMode {
		// Write mode requires single test
		if len(testNums) != 1 {
			return fmt.Errorf("write mode requires exactly one test")
		}
		modes.RunWrite(testNums[0], showData, showNotify)
		return nil
	} else if interactiveMode {
		modes.RunInteractive(startTestID)
		return nil
	} else if summaryMode {
		modes.RunSummary(testNums)
		return nil
	} else {
		// Table mode - call UrlTable directly with provided testNums
		output := display.UrlTable(testNums, true) // runTests = true
		fmt.Print(output)
		return nil
	}
}


