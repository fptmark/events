package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"

	"github.com/spf13/cobra"

	"query-verify/pkg/display"
	"query-verify/pkg/modes"
	"query-verify/pkg/parser"
)

var (
	resultsFile     string
	showAllData     bool
	showNotifications bool
	verifyMode      bool
	listMode        bool
	allMode         bool
)

func main() {
	var rootCmd = &cobra.Command{
		Use:   "query-verify [test-number]",
		Short: "Query and verify API test results",
		Long: `Query and verify API test results from results.json.

Usage examples:
  query-verify                    # List all URLs with indices
  query-verify 81                 # Show summary for test 81
  query-verify 81 --data          # Show test 81 with all data
  query-verify 81 --notify        # Show test 81 with all notifications
  query-verify --verify           # Interactive verification starting from test 1
  query-verify --verify 81        # Interactive verification starting from test 81
  query-verify --all              # Run verification on all tests and show summary table`,
		Args: cobra.MaximumNArgs(1),
		Run:  runCommand,
	}

	rootCmd.Flags().StringVarP(&resultsFile, "results", "r", "results.json", "Path to results.json file")
	rootCmd.Flags().BoolVarP(&showAllData, "data", "d", false, "Show all data records (default: first record only for arrays)")
	rootCmd.Flags().BoolVarP(&showNotifications, "notify", "n", false, "Show all notifications (default: truncated for arrays)")
	rootCmd.Flags().BoolVarP(&verifyMode, "verify", "v", false, "Enable verification mode")
	rootCmd.Flags().BoolVarP(&listMode, "list", "l", false, "List all URLs with indices")
	rootCmd.Flags().BoolVarP(&allMode, "all", "a", false, "Run verification on all tests and show summary table")

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runCommand(cmd *cobra.Command, args []string) {
	// Resolve absolute path to results file
	absResultsFile, err := filepath.Abs(resultsFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error resolving results file path: %v\n", err)
		os.Exit(1)
	}

	// Check if results file exists
	if _, err := os.Stat(absResultsFile); os.IsNotExist(err) {
		fmt.Fprintf(os.Stderr, "Error: %s not found\n", absResultsFile)
		os.Exit(1)
	}

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
		totalTests, err := parser.CountTests(absResultsFile)
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
	if allMode {
		// All mode - run verification on all tests and show summary table
		modes.RunAllMode(absResultsFile)
	} else if verifyMode {
		// Verification mode (interactive or single test)
		modes.RunVerifyMode(absResultsFile, testID)
	} else if listMode || testID == 0 {
		// List mode (no test ID provided or explicit --list)
		modes.RunListMode(absResultsFile)
	} else {
		// Summary/data/notify mode (test ID provided)
		options := display.DisplayOptions{
			ShowAllData:       showAllData,
			ShowNotifications: showNotifications,
		}
		modes.RunSummaryMode(absResultsFile, testID, options)
	}
}