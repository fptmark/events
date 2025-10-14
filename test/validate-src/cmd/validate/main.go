package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/spf13/cobra"

	"validate/pkg/core"
	"validate/pkg/display"
	"validate/pkg/modes"
	"validate/pkg/tests"
)

const (
	DefaultServerURL    = "http://localhost:5500"
	DefaultUserCount    = 87
	DefaultAccountCount = 31
)

var (
	// Show modes (informational only)
	listMode bool
	testMode bool

	// Run modes (mutually exclusive)
	interactiveMode bool
	writeMode       bool
	summaryMode     bool
	curlMode        bool
	testCategories  string

	// Output expansion (for interactive and write modes)
	showData   bool
	showNotify bool

	// Database reset (always honored)
	resetSpec string

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
  validate --reset                  # Reset database and populate with default counts (87 users, 31 accounts)
  validate --reset=100,50           # Reset database and populate with 100 users, 50 accounts`,
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
	rootCmd.Flags().BoolVarP(&curlMode, "curl", "c", false, "Generate and execute curl command (requires test number)")

	// Output expansion (for interactive and write modes)
	rootCmd.Flags().BoolVarP(&showData, "data", "d", false, "Show full data records")
	rootCmd.Flags().BoolVarP(&showNotify, "notify", "n", false, "Show notification records")

	// Database reset (always honored)
	rootCmd.Flags().StringVarP(&resetSpec, "reset", "r", "", "Reset database and populate test data (optional: users,accounts)")
	rootCmd.Flag("reset").NoOptDefVal = "defaults" // Allow --reset without value (uses defaults)
	rootCmd.Flags().BoolVarP(&verbose, "verbose", "v", false, "verbose output (for debugging)")

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runCommand(cmd *cobra.Command, args []string) {
	// Validate flag combinations and execute appropriate mode
	if err := validateAndExecute(cmd, args); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %s\n", err)
		os.Exit(1)
	}
}

func validateAndExecute(cmd *cobra.Command, args []string) error {
	// Parse reset spec for user/account counts
	numUsers := DefaultUserCount
	numAccounts := DefaultAccountCount

	// Check if --reset flag was provided
	if cmd.Flags().Changed("reset") {
		// If resetSpec is "defaults" (from NoOptDefVal), use defaults
		if resetSpec != "" && resetSpec != "defaults" {
			// --reset=users,accounts format
			parts := strings.Split(resetSpec, ",")
			if len(parts) == 2 {
				var err error
				numUsers, err = strconv.Atoi(strings.TrimSpace(parts[0]))
				if err != nil {
					return fmt.Errorf("invalid user count in --reset: %s", parts[0])
				}
				numAccounts, err = strconv.Atoi(strings.TrimSpace(parts[1]))
				if err != nil {
					return fmt.Errorf("invalid account count in --reset: %s", parts[1])
				}
			} else {
				return fmt.Errorf("invalid --reset format, expected: --reset=users,accounts")
			}
		}
		// else: --reset with no value uses defaults (numUsers and numAccounts already set)
	}

	// Set global config (now in core package)
	core.SetConfig(DefaultServerURL, verbose, numUsers, numAccounts)

	// Get test categories if specified
	var testNums []int
	hasTestCategories := cmd.Flags().Changed("test") && testCategories != "show"

	// Parse test number from args if provided
	if len(args) > 0 {
		testNum, err := strconv.Atoi(args[0])
		if err != nil {
			return fmt.Errorf("invalid test number '%s' (must be a number)", args[0])
		}
		testNums = []int{testNum}
	}

	// Validate test number vs categories
	if len(testNums) > 0 && hasTestCategories {
		return fmt.Errorf("cannot combine --test=categories with test number")
	}

	// Get test numbers to run
	if hasTestCategories {
		testNums = getTestNumbers(testCategories)
	} else if len(testNums) == 0 {
		testNums = getAllTestNumbers()
	}

	// Handle show modes (now with filtered testNums)
	if listMode {
		display.ListTests(testNums) // Use filtered testNums, nil means list mode
		return nil
	} else if cmd.Flags().Changed("test") && testCategories == "show" {
		modes.ShowTestCategories()
		return nil
	}

	// Handle database reset if requested (standalone CLI operation)
	if cmd.Flags().Changed("reset") {
		if err := ResetAndPopulate(); err != nil {
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
	if curlMode {
		runModeCount++
	}
	if runModeCount > 1 {
		return fmt.Errorf("only one run mode allowed")
	}

	// Write and curl modes require exactly one test
	if writeMode && len(testNums) != 1 {
		return fmt.Errorf("write mode requires exactly one test number")
	}
	if curlMode && len(testNums) != 1 {
		return fmt.Errorf("curl mode requires exactly one test number")
	}

	// Interactive mode: start with first test in the filtered list
	if interactiveMode && len(testNums) > 1 {
		testNums = []int{testNums[0]}
	}

	return runTests(testNums)
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

func runTests(testNums []int) error {
	if curlMode {
		modes.RunCurl(testNums[0])
	} else if writeMode {
		modes.RunWrite(testNums[0], showData, showNotify)
	} else if interactiveMode {
		modes.RunInteractive(testNums[0])
	} else {
		EnsureTestData()
		if summaryMode {
			modes.RunSummary(testNums)
		} else {
			modes.RunTable(testNums)
		}
	}
	return nil
}

// ResetAndPopulate performs the complete database reset and population sequence
// Always shows before/after counts (used for explicit --reset flag and before table/summary mode)
func ResetAndPopulate() error {
	users, accounts := core.GetEntityCountsFromReport()
	fmt.Printf("Before Reset:  users=%d, accounts=%d\n", users, accounts)

	// Step 1: Clean database
	if err := core.CleanDatabase(); err != nil {
		return fmt.Errorf("failed to clean database: %w", err)
	}

	// Step 2: Populate test data
	if err := tests.PopulateTestData(core.NumAccounts, core.NumUsers); err != nil {
		return fmt.Errorf("failed to populate test data: %w", err)
	}

	users, accounts = core.GetEntityCountsFromReport()
	fmt.Printf("After Reset:   users=%d, accounts=%d\n", users, accounts)

	return nil
}

// EnsureTestData checks if sufficient test data exists, and auto-resets if needed
// Used before running tests in table/summary mode
func EnsureTestData() {
	users, accounts := core.GetEntityCountsFromReport()
	fmt.Printf("Initial records: %d users, %d accounts\n", users, accounts)

	if users < core.NumUsers || accounts < core.NumAccounts {
		fmt.Printf("Insufficient test data: have %d users, %d accounts; need %d users, %d accounts\n",
			users, accounts, core.NumUsers, core.NumAccounts)
		fmt.Println("Auto-resetting and populating database...")

		ResetAndPopulate()
	}
}
