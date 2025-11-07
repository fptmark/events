package dynamic

import "validate/pkg/types"

// TestEntry defines a dynamic test
type TestEntry struct {
	Name        string
	Description string
	TestClass   string
	Function    func() (*types.TestResult, error)
}

// All dynamic tests registered here
var allTests = []TestEntry{
	// Pagination tests
	{"testPaginationDefault", "Pagination test - sorted by ID", "dynamic", testPaginationDefault},
	{"testPaginationById", "Pagination test - sorted by ID", "dynamic", testPaginationById},
	{"testPaginationByUserName", "Pagination test - sorted by username", "dynamic", testPaginationByUserName},

	// Admin tests
	{"testMetadata", "Get system metadata", "dynamic", testMetadata},
	{"testDbReport", "Get database status report", "dynamic", testDbReport},
	{"testDbInit", "Initialize database confirmation page", "dynamic", testDbInit},

	// Auth tests
	{"testAuth", "Redis authentication workflow (login, refresh, logout)", "dynamic", testAuth},

	// Authz tests (include permissions verification)
	{"testAuthzAdmin", "Authorization test - Admin role (cruds)", "authz", testAuthzAdmin},
	{"testAuthzMgr", "Authorization test - Manager role (crus)", "authz", testAuthzMgr},
	{"testAuthzRep", "Authorization test - Representative role (ru)", "authz", testAuthzRep},
}

// GetDynamicTestCases returns test case definitions for dynamic tests
func GetDynamicTestCases() []types.TestCase {
	testCases := make([]types.TestCase, len(allTests))
	for i, dt := range allTests {
		testCases[i] = types.TestCase{
			Method:      "GET",
			URL:         dt.Name,
			TestClass:   dt.TestClass,
			Description: dt.Description,
		}
	}
	return testCases
}

// GetDynamicTest returns the dynamic test function for the given name, or nil if not found
func GetDynamicTest(functionName string) func() (*types.TestResult, error) {
	for _, dt := range allTests {
		if dt.Name == functionName {
			return dt.Function
		}
	}
	return nil
}
