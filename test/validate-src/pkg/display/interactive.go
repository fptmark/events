package display

import (
	"bufio"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"

	"validate/pkg/types"
)

// InteractiveDisplay handles the interactive display of verification results
type InteractiveDisplay struct {
	reader *bufio.Reader
}

// NewInteractiveDisplay creates a new interactive display instance
func NewInteractiveDisplay() *InteractiveDisplay {
	return &InteractiveDisplay{
		reader: bufio.NewReader(os.Stdin),
	}
}

// ShowVerification displays verification results for a test case
func (d *InteractiveDisplay) ShowVerification(result *types.VerificationResult) {
	d.printHeader(result)
	d.printFields(result)
	d.printSummary(result)
}

// ShowVerificationWithSummary displays both summary and verification results
func (d *InteractiveDisplay) ShowVerificationWithSummary(summaryOutput string, result *types.VerificationResult) {
	d.clearScreen()
	// Print the summary first
	fmt.Print(summaryOutput)
	fmt.Println()
	// Then print verification results
	d.printHeader(result)
	d.printFields(result)
	d.printSummary(result)
}

// GetNavigation prompts user and waits for navigation command
// Returns: "next", "previous", "quit", or a number as string (e.g. "123")
func (d *InteractiveDisplay) GetNavigation() string {
	fmt.Print("\nPress SPACE to continue, '-' for previous, 'data'/'notify' for details, number for specific test, 'q' to quit, 'h' for help: ")

	// Read line input
	line, _ := d.reader.ReadString('\n')
	line = strings.ToLower(strings.TrimSpace(line))

	switch {
	case len(line) == 0:
		return "next"
	case line[0] == 'q':
		return "quit"
	case line[0] == '-':
		return "previous"
	case strings.ToLower(line) == "data":
		return "data"
	case strings.ToLower(line) == "notify":
		return "notify"
	default:
		// Check if it's a number for goto specific test
		if testID, parseErr := strconv.Atoi(line); parseErr == nil && testID > 0 {
			return line // Return the number as string
		}
	}

	// fallthrough to help
	return "help"
}

// WaitForEnter waits for user to press enter
func (d *InteractiveDisplay) WaitForEnter() {
	fmt.Print("Press enter to continue...")
	_, _ = d.reader.ReadString('\n')
}

// readSingleChar attempts to read a single character without waiting for Enter
// func (d *InteractiveDisplay) readSingleChar() (byte, error) {
// 	// This is a simplified implementation that works on Unix-like systems
// 	// For production, you might want to use a library like termbox-go
// 	var buf [1]byte
// 	_, err := syscall.Read(0, buf[:])
// 	return buf[0], err
// }

// clearScreen clears the terminal screen
func (d *InteractiveDisplay) clearScreen() {
	fmt.Print("\033[2J\033[H")
}

// printHeader displays the test case header information
func (d *InteractiveDisplay) printHeader(result *types.VerificationResult) {
	fmt.Printf("═══════════════════════════════════════════════════════════════════════════════\n")
	fmt.Printf("                           TEST VERIFICATION REPORT                           \n")
	fmt.Printf("═══════════════════════════════════════════════════════════════════════════════\n\n")

	fmt.Printf("Test ID:     %d\n", result.TestID)
	fmt.Printf("URL:         %s\n", result.URL)
	fmt.Printf("Description: %s\n", result.Description)
	fmt.Printf("Status:      %s\n", d.getStatusDisplay(result.Passed))
	fmt.Println()
}

// printFields displays the extracted field values
func (d *InteractiveDisplay) printFields(result *types.VerificationResult) {
	if len(result.Fields) == 0 {
		fmt.Println("No verification fields found.")
		return
	}

	// Sort field names for consistent display
	var fieldNames []string
	for fieldName := range result.Fields {
		fieldNames = append(fieldNames, fieldName)
	}
	sort.Strings(fieldNames)

	// Group fields by type
	sortFields := []string{}
	filterFields := []string{}
	viewFields := []string{}

	for _, fieldName := range fieldNames {
		if strings.HasPrefix(fieldName, "sort_") {
			sortFields = append(sortFields, fieldName)
		} else if strings.HasPrefix(fieldName, "filter_") {
			filterFields = append(filterFields, fieldName)
		} else if strings.HasPrefix(fieldName, "view_") {
			viewFields = append(viewFields, fieldName)
		}
	}

	// Display sort fields
	if len(sortFields) > 0 {
		fmt.Printf("┌─ SORT FIELDS ────────────────────────────────────────────────────────────────┐\n")
		for _, fieldName := range sortFields {
			displayName := strings.TrimPrefix(fieldName, "sort_")
			values := result.Fields[fieldName]
			fmt.Printf("│ %-15s: %s\n", displayName, d.formatValues(values))
		}
		fmt.Printf("└──────────────────────────────────────────────────────────────────────────────┘\n\n")
	}

	// Display filter fields
	if len(filterFields) > 0 {
		fmt.Printf("┌─ FILTER FIELDS ──────────────────────────────────────────────────────────────┐\n")
		for _, fieldName := range filterFields {
			displayName := strings.TrimPrefix(fieldName, "filter_")
			values := result.Fields[fieldName]
			fmt.Printf("│ %-15s: %s\n", displayName, d.formatValues(values))
		}
		fmt.Printf("└──────────────────────────────────────────────────────────────────────────────┘\n\n")
	}

	// Display view fields
	if len(viewFields) > 0 {
		fmt.Printf("┌─ VIEW FIELDS ────────────────────────────────────────────────────────────────┐\n")
		for _, fieldName := range viewFields {
			displayName := strings.TrimPrefix(fieldName, "view_")
			values := result.Fields[fieldName]
			fmt.Printf("│ %-15s: %s\n", displayName, d.formatValues(values))
		}
		fmt.Printf("└──────────────────────────────────────────────────────────────────────────────┘\n\n")
	}
}

// printSummary displays the verification summary and any issues
func (d *InteractiveDisplay) printSummary(result *types.VerificationResult) {
	fmt.Printf("┌─ VERIFICATION SUMMARY ───────────────────────────────────────────────────────┐\n")
	fmt.Printf("│ Overall Result: %s\n", d.getStatusDisplay(result.Passed))

	if len(result.Issues) > 0 {
		fmt.Printf("│ Issues Found:   %d\n", len(result.Issues))
		fmt.Printf("├──────────────────────────────────────────────────────────────────────────────┤\n")
		for i, issue := range result.Issues {
			fmt.Printf("│ %d. %s\n", i+1, d.wrapText(issue, 75))
		}
	} else {
		fmt.Printf("│ Issues Found:   None\n")
	}
	fmt.Printf("└──────────────────────────────────────────────────────────────────────────────┘\n")
}

// formatValues formats an array of values for display
func (d *InteractiveDisplay) formatValues(values interface{}) string {
	if values == nil {
		return "null"
	}

	if valSlice, ok := values.([]interface{}); ok {
		if len(valSlice) == 0 {
			return "[]"
		}

		var strValues []string
		for i, val := range valSlice {
			if i >= 10 { // Limit display to first 10 values
				strValues = append(strValues, "...")
				break
			}
			strValues = append(strValues, fmt.Sprintf("%v", val))
		}
		return fmt.Sprintf("[%s]", strings.Join(strValues, ", "))
	}

	return fmt.Sprintf("%v", values)
}

// getStatusDisplay returns a colored status display string
func (d *InteractiveDisplay) getStatusDisplay(passed bool) string {
	if passed {
		return "\033[32m✓ PASS\033[0m"
	}
	return "\033[31m✗ FAIL\033[0m"
}

// wrapText wraps text to fit within the specified width
func (d *InteractiveDisplay) wrapText(text string, width int) string {
	if len(text) <= width {
		return text
	}

	// Simple word wrap
	words := strings.Split(text, " ")
	var lines []string
	var currentLine string

	for _, word := range words {
		if len(currentLine)+len(word)+1 <= width {
			if currentLine != "" {
				currentLine += " "
			}
			currentLine += word
		} else {
			if currentLine != "" {
				lines = append(lines, currentLine)
			}
			currentLine = word
		}
	}

	if currentLine != "" {
		lines = append(lines, currentLine)
	}

	// Join with proper indentation for wrapped lines
	result := lines[0]
	for i := 1; i < len(lines); i++ {
		result += "\n│   " + lines[i]
	}

	return result
}

// ShowData displays the test case with all data records (like --data flag)
func (d *InteractiveDisplay) ShowData(testCase *types.TestCase) {
	options := DisplayOptions{
		ShowAllData:       true,
		ShowNotifications: false,
	}
	output, err := FormatTestResponse(testCase, options)
	if err != nil {
		fmt.Printf("Error formatting response: %v\n", err)
		return
	}
	d.clearScreen()
	fmt.Print(output)
	d.WaitForEnter()
}

// ShowNotifications displays the test case with all notifications (like --notify flag)
func (d *InteractiveDisplay) ShowNotifications(testCase *types.TestCase) {
	options := DisplayOptions{
		ShowAllData:       false,
		ShowNotifications: true,
	}
	output, err := FormatTestResponse(testCase, options)
	if err != nil {
		fmt.Printf("Error formatting response: %v\n", err)
		return
	}
	d.clearScreen()
	fmt.Print(output)
	d.WaitForEnter()
}

// ShowHelp displays help information
func (d *InteractiveDisplay) ShowHelp() {
	fmt.Printf("\n┌─ HELP ───────────────────────────────────────────────────────────────────────┐\n")
	fmt.Printf("│ Navigation Controls:                                                         │\n")
	fmt.Printf("│   SPACE - Continue to next test                                             │\n")
	fmt.Printf("│   -     - Go back to previous test                                          │\n")
	fmt.Printf("│   123   - Go to specific test number (e.g., 123)                           │\n")
	fmt.Printf("│   data  - Show all data records for current test                           │\n")
	fmt.Printf("│   notify- Show all notifications for current test                          │\n")
	fmt.Printf("│   q     - Quit the verification session                                     │\n")
	fmt.Printf("│   h     - Show this help message                                            │\n")
	fmt.Printf("│                                                                              │\n")
	fmt.Printf("│ Field Types:                                                                 │\n")
	fmt.Printf("│   Sort Fields   - Values extracted from sort parameters                     │\n")
	fmt.Printf("│   Filter Fields - Values extracted from filter parameters                   │\n")
	fmt.Printf("│   View Fields   - Values extracted from view/expand parameters              │\n")
	fmt.Printf("│                                                                              │\n")
	fmt.Printf("│ Verification checks sort order and filter criteria automatically.           │\n")
	fmt.Printf("└──────────────────────────────────────────────────────────────────────────────┘\n\n")
}
