package modes

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"validate/pkg/datagen"
	"validate/pkg/tests"
	"validate/pkg/types"
)

// RunCurl generates and executes curl command for a single test
func RunCurl(testNum int) {
	allTests := tests.GetAllTestCases()
	if testNum < 1 || testNum > len(allTests) {
		fmt.Fprintf(os.Stderr, "Error: test number %d out of range (1-%d)\n", testNum, len(allTests))
		os.Exit(1)
	}

	testCase := allTests[testNum-1]

	// Build curl command
	curlCmd := buildCurlCommand(&testCase)

	// Echo the command
	fmt.Printf("# Test %d: %s\n", testNum, testCase.Description)
	fmt.Printf("%s\n\n", curlCmd)

	// Execute the command
	cmd := exec.Command("sh", "-c", curlCmd)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "\nError executing curl: %v\n", err)
		os.Exit(1)
	}
}

func buildCurlCommand(testCase *types.TestCase) string {
	serverURL := datagen.GlobalConfig.ServerURL
	// Remove trailing slash from serverURL if present
	serverURL = strings.TrimSuffix(serverURL, "/")
	// testCase.URL already includes /api/ prefix with leading slash
	url := serverURL + testCase.URL

	// Build curl command parts
	parts := []string{"curl", "-X", testCase.Method}

	// Add headers
	parts = append(parts, "-H", "'Content-Type: application/json'")

	// Add request body for POST/PUT
	if testCase.RequestBody != nil && (testCase.Method == "POST" || testCase.Method == "PUT") {
		jsonBody, err := json.Marshal(testCase.RequestBody)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error marshaling request body: %v\n", err)
			os.Exit(1)
		}
		// Escape single quotes in JSON for shell
		bodyStr := string(jsonBody)
		bodyStr = strings.ReplaceAll(bodyStr, "'", "'\\''")
		parts = append(parts, "-d", fmt.Sprintf("'%s'", bodyStr))
	}

	// Add verbose flag for debugging
	parts = append(parts, "-v")

	// Add URL (quote it to handle special characters)
	parts = append(parts, fmt.Sprintf("'%s'", url))

	return strings.Join(parts, " ")
}
