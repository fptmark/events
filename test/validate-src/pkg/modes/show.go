package modes

import (
	"fmt"
	"sort"
	"strings"

	statictestsuite "validate/pkg/static-test-suite"
)

// ShowURLList displays all URLs with test#, category, and /api/path
func ShowURLList() {
	fmt.Println("Available URLs:")
	fmt.Printf("%-4s %-12s %s\n", "Test", "Category", "URL")
	fmt.Println(strings.Repeat("-", 60))

	testCases := statictestsuite.GetAllTestCases()
	for i, testCase := range testCases {
		// Extract /api/path from full URL
		apiPath := extractAPIPath(testCase.URL)
		fmt.Printf("%-4d %-12s %s\n", i+1, testCase.TestClass, apiPath)
	}
}

// ShowTestCategories displays all available test categories
func ShowTestCategories() {
	allTests := statictestsuite.GetAllTestCases()
	categoryMap := make(map[string]int)

	// Count tests per category
	for _, test := range allTests {
		categoryMap[test.TestClass]++
	}

	// Sort categories alphabetically
	var categories []string
	for category := range categoryMap {
		categories = append(categories, category)
	}
	sort.Strings(categories)

	fmt.Println("Available test categories:")
	fmt.Println("========================")
	for _, category := range categories {
		fmt.Printf("%-10s (%d tests)\n", category, categoryMap[category])
	}
	fmt.Printf("\nTotal: %d tests across %d categories\n", len(allTests), len(categories))
	fmt.Println("\nUsage: validate --test=category1,category2 to run specific categories")
}

// extractAPIPath extracts the /api/path portion from a full URL
func extractAPIPath(url string) string {
	// Find the position of "/api/" and return everything from there
	apiIndex := strings.Index(url, "/api/")
	if apiIndex != -1 {
		return url[apiIndex:] // Include "/api/"
	}
	return url // fallback to full URL if "/api/" not found
}