package main

import (
	"fmt"
	"os"
	"strconv"

	"github.com/spf13/cobra"

	"validate/pkg/display"
	"validate/pkg/modes"
	"validate/pkg/parser"
)

var (
	showAllData     bool
	showNotifications bool
	verifyMode      bool
	listMode        bool
	allMode         bool
	summaryMode     bool
	testMode        bool
	testCategories  string
)

func main() {
	var rootCmd = &cobra.Command{
		Use:   "validate [test-number]",
		Short: "Query and verify API test results",
		Long: `Execute and verify API tests in real-time.

Usage examples:
  validate                    # List all available test URLs
  validate 81                 # Execute and show test 81
  validate 81 --data          # Execute test 81 with all data
  validate 81 --notify        # Execute test 81 with all notifications
  validate --verify           # Interactive verification starting from test 1
  validate --verify 81        # Interactive verification starting from test 81
  validate --all              # Run verification on all tests and show summary table
  validate --summary          # Show only summary statistics`,
		Args: cobra.MaximumNArgs(1),
		Run:  runCommand,
	}

	rootCmd.Flags().BoolVarP(&showAllData, "data", "d", false, "Show all data records (default: first record only for arrays)")
	rootCmd.Flags().BoolVarP(&showNotifications, "notify", "n", false, "Show all notifications (default: truncated for arrays)")
	rootCmd.Flags().BoolVarP(&verifyMode, "verify", "v", false, "Enable verification mode")
	rootCmd.Flags().BoolVarP(&listMode, "list", "l", false, "List all URLs with indices")
	rootCmd.Flags().BoolVarP(&allMode, "all", "a", false, "Run verification on all tests and show summary table")
	rootCmd.Flags().BoolVarP(&summaryMode, "summary", "s", false, "Show only summary statistics")

	// Custom flag that supports both -t and -t=categories
	rootCmd.Flags().StringVarP(&testCategories, "test", "t", "", "Show all test categories or run specific categories (e.g., -t=page,sort)")
	rootCmd.Flag("test").NoOptDefVal = "all"

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runCommand(cmd *cobra.Command, args []string) {
	// Initialize HTTP mode
	parser.InitHTTPMode()

	// Determine mode based on arguments and flags
	var testID int
	if len(args) > 0 {
		id, err := strconv.Atoi(args[0])
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error: Invalid test ID '%s' (must be a number)\n", args[0])
			os.Exit(1)
		}
		testID = id
	}

	// Validate test ID if provided
	if testID > 0 {
		totalTests, err := parser.CountTests()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error counting tests: %v\n", err)
			os.Exit(1)
		}
		if testID > totalTests {
			fmt.Fprintf(os.Stderr, "Error: Invalid index %d\n", testID)
			fmt.Println()
			listMode = true // Fall back to list mode
			testID = 0
		}
	}

	// Execute the appropriate mode
	if cmd.Flags().Changed("test") {
		// Test mode - show categories or run specific categories
		modes.RunTestMode(testCategories)
	} else if summaryMode {
		// Summary mode - show only summary statistics
		modes.RunSummaryOnlyMode()
	} else if allMode {
		// All mode - run verification on all tests and show summary table
		modes.RunAllMode()
	} else if verifyMode {
		// Verification mode (interactive or single test)
		modes.RunVerifyMode(testID)
	} else if listMode || testID == 0 {
		// List mode (no test ID provided or explicit --list)
		modes.RunListMode()
	} else {
		// Summary/data/notify mode (test ID provided)
		options := display.DisplayOptions{
			ShowAllData:       showAllData,
			ShowNotifications: showNotifications,
		}
		modes.RunSummaryMode(testID, options)
	}
}