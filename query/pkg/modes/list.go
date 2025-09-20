package modes

import (
	"fmt"
	"os/exec"
	"strings"
)

// RunListMode displays all URLs with their test indices
func RunListMode(resultsFile string) {
	fmt.Println("Available URLs:")

	// Use jq to list all keys in original order with indices
	cmd := exec.Command("jq", "-r", "keys_unsorted | to_entries | .[] | \"\\(.key + 1). \\(.value)\"", resultsFile)
	output, err := cmd.Output()
	if err != nil {
		fmt.Printf("Error listing URLs: %v\n", err)
		return
	}

	// The output already includes the numbering from jq, so just print it
	lines := strings.Split(strings.TrimSpace(string(output)), "\n")
	for _, line := range lines {
		fmt.Println(line)
	}
}