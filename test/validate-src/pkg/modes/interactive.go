package modes

import (
	"fmt"
	"os"
	"strconv"

	"validate/pkg/core"
	"validate/pkg/display"
	"validate/pkg/parser"
)

// RunInteractive runs tests in interactive verification mode
func RunInteractive(startTestNum int) {
	totalTests, err := parser.CountTests()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error counting tests: %v\n", err)
		os.Exit(1)
	}

	// Determine starting test
	currentID := 1
	if startTestNum > 0 {
		if startTestNum > totalTests {
			fmt.Fprintf(os.Stderr, "Test ID %d exceeds total tests (%d)\n", startTestNum, totalTests)
			os.Exit(1)
		}
		currentID = startTestNum
	}

	interactiveDisplay := display.NewInteractiveDisplay()
	fmt.Printf("Starting verification from test %d (total: %d tests)\n", currentID, totalTests)

mainLoop:
	for {
		// Validate bounds
		if currentID < 1 {
			currentID = 1
		}
		if currentID > totalTests {
			currentID = totalTests
		}

		// Run test and validation
		result, err := core.RunTest(currentID)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error running test %d: %v\n", currentID, err)
			currentID++
			if currentID > totalTests {
				break
			}
			continue
		}

		validate := core.ValidateTest(currentID, result)

		// Show summary and verification
		showInteractiveTest(result, validate, interactiveDisplay)

		// Handle navigation
		if currentID >= totalTests {
			fmt.Println("\nReached end of test suite.")
		}

		action := interactiveDisplay.GetNavigation()
		switch action {
		case "quit":
			fmt.Println("\nVerification session ended by user.")
			break mainLoop
		case "data":
			showTestData(result)
		case "notify":
			showTestNotifications(result)
		case "next":
			if currentID < totalTests {
				currentID++
			} else {
				fmt.Println("Already at last test.")
				interactiveDisplay.WaitForEnter()
			}
		case "previous":
			if currentID > 1 {
				currentID--
			} else {
				fmt.Println("Already at first test.")
				interactiveDisplay.WaitForEnter()
			}
		case "help":
			interactiveDisplay.ShowHelp()
			interactiveDisplay.WaitForEnter()
		default:
			// Try to parse as test number
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

// showInteractiveTest displays test summary and verification for interactive mode
func showInteractiveTest(result *core.TestResult, validate *core.ValidationResult, interactiveDisplay *display.InteractiveDisplay) {
	// Format summary header
	summaryHeader := fmt.Sprintf("══════════════════════════════════════════════════════════════════════════════\n")
	summaryHeader += fmt.Sprintf("                              TEST SUMMARY                                   \n")
	summaryHeader += fmt.Sprintf("══════════════════════════════════════════════════════════════════════════════\n\n")

	// Use write mode formatting for summary
	RunWrite(result.ID, false, false)

	// Convert to old verification result format for display compatibility
	fields := make(map[string]interface{})
	for key, values := range validate.Fields {
		fields[key] = values
	}

	// Show verification results
	fmt.Printf("\n=== VERIFICATION RESULTS ===\n")
	if validate.OK {
		fmt.Printf("Status: \033[32mPASS\033[0m\n")
	} else {
		fmt.Printf("Status: \033[31mFAIL\033[0m\n")
		for _, issue := range validate.Issues {
			fmt.Printf("Issue: %s\n", issue)
		}
	}

	// Show extracted fields
	if len(validate.Fields) > 0 {
		fmt.Printf("\nExtracted Fields:\n")
		for fieldName, values := range validate.Fields {
			fmt.Printf("  %s: [", fieldName)
			for i, value := range values {
				if i > 0 {
					fmt.Printf(", ")
				}
				if i >= 10 {
					fmt.Printf("...")
					break
				}
				fmt.Printf("%v", value)
			}
			fmt.Printf("]\n")
		}
	}
	fmt.Println()
}

// showTestData displays full test data
func showTestData(result *core.TestResult) {
	fmt.Printf("\n=== FULL DATA ===\n")
	RunWrite(result.ID, true, false)
	fmt.Printf("Press Enter to continue...")
	fmt.Scanln()
}

// showTestNotifications displays full test notifications
func showTestNotifications(result *core.TestResult) {
	fmt.Printf("\n=== FULL NOTIFICATIONS ===\n")
	RunWrite(result.ID, false, true)
	fmt.Printf("Press Enter to continue...")
	fmt.Scanln()
}