package modes

import (
	"fmt"
	"os"

	"query-verify/pkg/display"
	"query-verify/pkg/parser"
	"query-verify/pkg/verifier"
)

// RunVerifyMode runs verification mode (interactive or single test)
func RunVerifyMode(resultsFile string, testID int) {
	// Count total tests
	totalTests, err := parser.CountTests(resultsFile)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error counting tests: %v\n", err)
		os.Exit(1)
	}

	// Determine starting test ID
	startID := 1
	if testID > 0 {
		if testID > totalTests {
			fmt.Fprintf(os.Stderr, "Test ID %d exceeds total tests (%d)\n", testID, totalTests)
			os.Exit(1)
		}
		startID = testID
	}

	// Initialize components
	visualVerifier := verifier.NewVisualVerifier()
	interactiveDisplay := display.NewInteractiveDisplay()

	fmt.Printf("Starting verification from test %d (total: %d tests)\n", startID, totalTests)
	fmt.Println("Loading test data...")

	// Run interactive verification
	for currentID := startID; currentID <= totalTests; currentID++ {
		// Load test case
		testCase, err := parser.LoadTestCase(currentID, resultsFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error loading test case %d: %v\n", currentID, err)
			continue
		}

		// Prepare summary output
		summaryHeader := fmt.Sprintf("══════════════════════════════════════════════════════════════════════════════\n")
		summaryHeader += fmt.Sprintf("                              TEST SUMMARY                                   \n")
		summaryHeader += fmt.Sprintf("══════════════════════════════════════════════════════════════════════════════\n\n")

		// Display the summary with default truncation (like ./query-verify 1)
		summaryOptions := display.DisplayOptions{
			ShowAllData:       false, // Show only first record
			ShowNotifications: false, // Truncate notifications
		}
		summaryOutput, err := display.FormatTestResponse(testCase, summaryOptions)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error formatting summary: %v\n", err)
			continue
		}

		fullSummary := summaryHeader + summaryOutput

		// Extract verification fields
		extraction := parser.ExtractVerificationFields(testCase)

		// Perform verification
		verificationResult := visualVerifier.Verify(testCase, extraction)

		// Display both summary and verification results
		interactiveDisplay.ShowVerificationWithSummary(fullSummary, verificationResult)

		// Wait for user input (unless it's the last test)
		if currentID < totalTests {
			if !interactiveDisplay.WaitForContinue() {
				fmt.Println("\nVerification session ended by user.")
				break
			}
		} else {
			fmt.Println("\nReached end of test suite.")
			fmt.Println("Press any key to exit...")
			interactiveDisplay.WaitForContinue()
		}
	}

	fmt.Println("Verification complete.")
}