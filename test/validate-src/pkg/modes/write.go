package modes

import (
	"fmt"
	"os"
	"strings"

	"validate/pkg/core"
	"validate/pkg/display"
	"validate/pkg/types"
)

// RunWrite runs a single test and outputs formatted result
func RunWrite(testNum int, fullData bool, fullNotifications bool) {
	result, err := core.RunTest(testNum)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error running test %d: %v\n", testNum, err)
		os.Exit(1)
	}

	// Create TestCase for display compatibility (same pattern as interactive mode)
	testCase := &types.TestCase{
		ID:              result.ID,
		URL:             result.URL,
		Description:     result.Description,
		TestClass:       result.TestClass,
		ActualStatus:    result.StatusCode,
		RawResponseBody: result.RawResponseBody,
		Result: types.TestResult{
			Data:          result.Data,
			Notifications: result.Notifications,
			Status:        result.Status,
		},
	}

	// Use existing display formatter with options
	options := display.DisplayOptions{
		ShowAllData:       fullData,
		ShowNotifications: fullNotifications,
	}

	output, err := display.FormatTestResponse(testCase, options)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error formatting response: %v\n", err)
		os.Exit(1)
	}

	// Replace "Status:" with "HTTP Status:" to match our format
	output = strings.Replace(output, "Status: ", "HTTP Status: ", 1)

	fmt.Print(output)
}

