package modes

import (
	"fmt"
	statictestsuite "validate/pkg/static-test-suite"
)

// RunListMode displays all URLs with their test indices
func RunListMode() {
	fmt.Println("Available URLs:")

	testCases := statictestsuite.GetAllTestCases()
	for i, testCase := range testCases {
		fmt.Printf("%d. %s\n", i+1, testCase.URL)
	}
}