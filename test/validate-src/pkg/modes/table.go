package modes

import (
	"fmt"
	"os"

	"validate/pkg/display"
	"validate/pkg/parser"
)

// RunTable runs all tests and displays results in table format
func RunTable() {
	totalTests, err := parser.CountTests()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error counting tests: %v\n", err)
		os.Exit(1)
	}

	// Create test numbers array
	var testNumbers []int
	for i := 1; i <= totalTests; i++ {
		testNumbers = append(testNumbers, i)
	}

	// Use unified UrlTable function
	output := display.UrlTable(testNumbers, true) // runTests = true
	fmt.Print(output)
}