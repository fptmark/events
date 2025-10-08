package core

import (
	"fmt"

	"validate/pkg/httpclient"
	"validate/pkg/tests"
	"validate/pkg/types"
)

// ExecuteTests runs all tests and returns results
func ExecuteTests(testNumbers []int) ([]*types.TestResult, error) {
	allTestCases := tests.GetAllTestCases()
	totalTests := len(allTestCases)

	// Validate all test numbers first
	for _, testNum := range testNumbers {
		if testNum < 1 || testNum > totalTests {
			return nil, fmt.Errorf("test number %d out of range (1-%d)", testNum, totalTests)
		}
	}

	results := make([]*types.TestResult, len(testNumbers))

	for i, testNum := range testNumbers {
		// Execute test
		result, err := httpclient.ExecuteTest(testNum)
		results[i] = result

		if err != nil || result == nil {
			continue
		}

		testCase := allTestCases[testNum-1]

		// Count warnings, request warnings, and errors in notifications
		if result.Notifications != nil {
			if notifMap, ok := result.Notifications.(map[string]interface{}); ok {
				if warningsMap, ok := notifMap["warnings"].(map[string]interface{}); ok {
					for _, entityWarnings := range warningsMap {
						if entityMap, ok := entityWarnings.(map[string]interface{}); ok {
							for _, entityErrors := range entityMap {
								if errorsList, ok := entityErrors.([]interface{}); ok {
									for _, errorItem := range errorsList {
										if errorMap, ok := errorItem.(map[string]interface{}); ok {
											if errorType, ok := errorMap["type"].(string); ok {
												switch errorType {
												case "warning":
													result.Warnings++
												case "request_warning":
													result.RequestWarnings++
												case "error":
													result.Errors++
												}
											}
										}
									}
								}
							}
						}
					}
				}
			}
		}

		// Determine pass/fail
		validation := ValidateTest(testNum, result)
		statusMatch := result.StatusCode == testCase.ExpectedStatus

		// Store pass/fail in result
		result.Passed = statusMatch && validation.OK && result.Errors == 0
	}

	return results, nil
}

