package modes

import (
	"fmt"
	"sort"
	"strings"

	"validate/pkg/static-test-suite"
)

// RunTestMode handles test category display and execution
func RunTestMode(categories string) {
	// Get all test cases
	allTests := statictestsuite.GetAllTestCases()

	// If no specific categories provided or "all", show all available categories
	if categories == "" || categories == "all" {
		showAllCategories(allTests)
		return
	}

	// Parse requested categories
	requestedCategories := strings.Split(categories, ",")
	for i := range requestedCategories {
		requestedCategories[i] = strings.TrimSpace(requestedCategories[i])
	}

	// Run tests for specific categories
	runCategoriesTests(requestedCategories)
}

// showAllCategories displays all available test categories
func showAllCategories(allTests []statictestsuite.TestCase) {
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
	fmt.Println("\nUsage: validate -t=category1,category2 to run specific categories")
}

// runCategoriesTests executes tests for specific categories
func runCategoriesTests(categories []string) {
	fmt.Printf("Running tests for categories: %s\n", strings.Join(categories, ", "))
	fmt.Println("=" + strings.Repeat("=", 50))

	for _, category := range categories {
		tests := statictestsuite.GetTestCasesByClass(category)
		if len(tests) == 0 {
			fmt.Printf("No tests found for category: %s\n", category)
			continue
		}

		fmt.Printf("\n%s tests (%d):\n", strings.ToUpper(category), len(tests))
		fmt.Println(strings.Repeat("-", 40))

		for i, test := range tests {
			fmt.Printf("%d. %s %s\n", i+1, test.Verb, test.URL)
			if test.Description != "" {
				fmt.Printf("   Description: %s\n", test.Description)
			}
		}
	}
}