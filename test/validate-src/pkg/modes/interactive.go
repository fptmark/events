package modes

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"validate/pkg/core"
	"validate/pkg/tests"
	"validate/pkg/types"
)

// RunInteractive runs tests in interactive verification mode
func RunInteractive(startTestNum int) {
	allTests := tests.GetAllTestCases()
	testNum := startTestNum

	fmt.Printf("Starting verification from test %d (total: %d tests)\n", testNum, len(allTests))

mainLoop:
	for {
		// Execute test
		results, err := core.ExecuteTests([]int{testNum})
		if err != nil {
			fmt.Fprintf(os.Stderr, "Unexpected error: %v\n", err)
			break
		}
		result := results[0]
		if result == nil {
			fmt.Fprintf(os.Stderr, "Error running test %d: no result\n", testNum)
			testNum++
			if testNum > len(allTests) {
				break
			}
			continue
		}

		// Clear screen and display test (default: truncated)
		fmt.Print("\033[2J\033[H")
		testCase := allTests[testNum-1]
		output := formatResult(&testCase, result, false, false)
		fmt.Print(output)

		// Handle navigation
		if testNum >= len(allTests) {
			fmt.Println("\nReached end of test suite.")
		}

		action := getNavigation()
		switch action {
		case "quit":
			fmt.Println("\nVerification session ended by user.")
			break mainLoop
		case "data":
			showTestData(result, &testCase)
		case "notify":
			showTestNotifications(result, &testCase)
		case "next":
			if testNum < len(allTests) {
				testNum++
			} else {
				fmt.Println("Already at last test.")
				waitForEnter()
			}
		case "previous":
			if testNum > 1 {
				testNum--
			} else {
				fmt.Println("Already at first test.")
				waitForEnter()
			}
		case "help":
			showHelp()
			waitForEnter()
		default:
			// Try to parse as test number
			if newTestNum, parseErr := strconv.Atoi(action); parseErr == nil {
				if newTestNum >= 1 && newTestNum <= len(allTests) {
					testNum = newTestNum
				} else {
					fmt.Printf("Invalid test ID: %d. Valid range: 1-%d\n", newTestNum, len(allTests))
					waitForEnter()
				}
			} else {
				fmt.Printf("Unknown action: %s\n", action)
				waitForEnter()
			}
		}
	}

	fmt.Println("Verification complete.")
}

// showTestData displays full test data
func showTestData(result *types.TestResult, testCase *types.TestCase) {
	fmt.Print("\033[2J\033[H") // Clear screen
	fmt.Printf("\n=== FULL DATA ===\n")
	output := formatResult(testCase, result, true, false)
	fmt.Print(output)
	fmt.Printf("Press Enter to continue...")
	fmt.Scanln()
}

// showTestNotifications displays full test notifications
func showTestNotifications(result *types.TestResult, testCase *types.TestCase) {
	fmt.Print("\033[2J\033[H") // Clear screen
	fmt.Printf("\n=== FULL NOTIFICATIONS ===\n")
	output := formatResult(testCase, result, false, true)
	fmt.Print(output)
	fmt.Printf("Press Enter to continue...")
	fmt.Scanln()
}

// getNavigation prompts user for navigation command
func getNavigation() string {
	reader := bufio.NewReader(os.Stdin)
	fmt.Print("\nAction [enter=next, b/-/p=previous, d=data, n=notify, h=help, q=quit, #=goto]: ")
	input, _ := reader.ReadString('\n')
	action := strings.TrimSpace(input)

	// Map shortcuts to full commands
	switch action {
	case "":
		return "next"
	case "p", "-", "b":
		return "previous"
	case "d":
		return "data"
	case "n":
		return "notify"
	case "h":
		return "help"
	case "q":
		return "quit"
	default:
		return action
	}
}

// waitForEnter waits for user to press Enter
func waitForEnter() {
	fmt.Print("Press Enter to continue...")
	bufio.NewReader(os.Stdin).ReadBytes('\n')
}

// showHelp displays help information
func showHelp() {
	fmt.Print("\033[2J\033[H") // Clear screen
	fmt.Println("=== INTERACTIVE MODE HELP ===")
	fmt.Println()
	fmt.Println("Navigation commands:")
	fmt.Println("  enter        - Go to next test")
	fmt.Println("  p            - Go to previous test")
	fmt.Println("  d            - Show full data for current test")
	fmt.Println("  n            - Show full notifications for current test")
	fmt.Println("  h            - Show this help")
	fmt.Println("  q            - Exit interactive mode")
	fmt.Println("  <number>     - Go to specific test number")
	fmt.Println()
}
