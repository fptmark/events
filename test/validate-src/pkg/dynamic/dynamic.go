package dynamic

import (
	"fmt"
	"validate/pkg/core"
)

// Map of function names to function pointers
var dynamicTests = map[string]func() (*core.TestResult, error){
	"testPaginationAggregation": testPaginationAggregation,
	// Add more dynamic tests here as needed
}

// GetFunction returns the dynamic test function for the given name, or nil if not found
func GetFunction(functionName string) func() (*core.TestResult, error) {
	if fn, exists := dynamicTests[functionName]; exists {
		return fn
	}
	return nil
}

// testPaginationAggregation - placeholder function that returns error for unimplemented dynamic test
func testPaginationAggregation() (*core.TestResult, error) {
	return nil, fmt.Errorf("testPaginationAggregation function not implemented yet")
}