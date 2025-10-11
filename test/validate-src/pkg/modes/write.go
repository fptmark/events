package modes

import (
	"fmt"
	"os"

	"validate/pkg/tests"
)

// RunWrite runs a single test and outputs formatted result
func RunWrite(testNum int, fullData bool, fullNotifications bool) {
	results, err := tests.ExecuteTests([]int{testNum})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	result := results[0]
	if result == nil {
		fmt.Fprintf(os.Stderr, "Error running test %d: no result returned\n", testNum)
		os.Exit(1)
	}

	allTests := tests.GetAllTestCases()
	testCase := allTests[testNum-1]

	output := formatResult(&testCase, result, fullData, fullNotifications)
	fmt.Print(output)
}

