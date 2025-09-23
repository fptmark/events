package modes

import (
	"fmt"
	"os"
	"strconv"

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

	// Run interactive verification with navigation support
	currentID := startID
mainLoop:
	for {
		// Validate current test ID bounds
		if currentID < 1 {
			currentID = 1
		}
		if currentID > totalTests {
			currentID = totalTests
		}

		// Load test case
		testCase, err := parser.LoadTestCase(currentID, resultsFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error loading test case %d: %v\n", currentID, err)
			currentID++
			if currentID > totalTests {
				break
			}
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
			currentID++
			if currentID > totalTests {
				break
			}
			continue
		}

		fullSummary := summaryHeader + summaryOutput

		// Extract verification fields
		extraction := parser.ExtractVerificationFields(testCase)

		// Perform verification
		verificationResult := visualVerifier.Verify(testCase, extraction)

		// Display both summary and verification results
		interactiveDisplay.ShowVerificationWithSummary(fullSummary, verificationResult)

		// Handle navigation - unified for all cases
		if currentID >= totalTests {
			fmt.Println("\nReached end of test suite.")
		}

		action := interactiveDisplay.GetNavigation()
		switch action {
		case "quit":
			fmt.Println("\nVerification session ended by user.")
			break mainLoop
		case "next":
			if currentID < totalTests {
				currentID++
			} else {
				fmt.Println("Already at last test.")
				interactiveDisplay.WaitForEnter()
			}
		case "previous":
			fmt.Println("Going to previous test...")
			if currentID > 1 {
				currentID--
			} else {
				fmt.Println("Already at first test.")
				interactiveDisplay.WaitForEnter()
			}
		case "help":
			interactiveDisplay.ShowHelp()
			interactiveDisplay.WaitForEnter()
			// Stay on current test after showing help
		default:
			// Must be a number string, try to parse it
			if testID, parseErr := strconv.Atoi(action); parseErr == nil {
				if testID >= 1 && testID <= totalTests {
					currentID = testID
				} else {
					fmt.Printf("Invalid test ID: %d. Valid range: 1-%d\n", testID, totalTests)
					interactiveDisplay.WaitForEnter()
				}
			} else {
				fmt.Printf("Unknown action: %s\n", action)
				interactiveDisplay.WaitForEnter()
			}
		}
	}

	fmt.Println("Verification complete.")
}
