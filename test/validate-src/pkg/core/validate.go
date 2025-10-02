package core

import (
	"validate/pkg/verifier"
)

// ValidationResult represents the result of test validation
type ValidationResult struct {
	OK     bool
	Issues []string
	Fields map[string][]interface{}
}

// ValidateTest validates a test result and returns validation status
func ValidateTest(testNum int, result *TestResult) *ValidationResult {
	// Prepare verification parameters
	params := verifier.TestParams{
		Sort:   result.Params.Sort,
		Filter: result.Params.Filter,
		Page:   result.Params.Page,
		Size:   result.Params.Size,
		View:   result.Params.View,
	}

	// Run verification
	verifyResult := verifier.Verifier.Verify(result.Data, params)

	// Convert to clean validation result
	return &ValidationResult{
		OK:     verifyResult.Passed,
		Issues: verifyResult.Issues,
		Fields: verifyResult.Fields,
	}
}