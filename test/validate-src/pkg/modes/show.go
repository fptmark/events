package modes

import (
	"fmt"
	"sort"

	"validate/pkg/tests"
)

// ShowTestCategories displays all available test categories
func ShowTestCategories() {
	allTests := tests.GetAllTestCases()
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