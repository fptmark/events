package generator

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"data-generator/pkg/testcases"
)

// Config holds configuration for data generation
type Config struct {
	ServerURL string `json:"server_url,omitempty"` // API server URL, defaults to localhost:5500
	Verbose   bool   `json:"-"`                    // Not from config file
}

// TestCategory represents a test category
type TestCategory struct {
	Name        string
	Description string
}


// LoadConfig loads configuration from file
func LoadConfig(filename string) (Config, error) {
	var config Config

	data, err := os.ReadFile(filename)
	if err != nil {
		return config, fmt.Errorf("failed to read config file %s: %w", filename, err)
	}

	if err := json.Unmarshal(data, &config); err != nil {
		return config, fmt.Errorf("failed to parse config file %s: %w", filename, err)
	}

	return config, nil
}

// GetAvailableCategories returns all available test categories
func GetAvailableCategories() []TestCategory {
	return []TestCategory{
		{"basic", "Basic CRUD operations and validation"},
		{"view", "View parameter FK testing"},
		{"sort", "Sorting operations"},
		{"page", "Pagination testing"},
		{"filter", "Filtering operations"},
		{"case", "Case sensitivity testing"},
		{"combo", "Complex parameter combinations"},
	}
}

// GenerateAll generates all test data and curl.sh script
func GenerateAll(config Config) error {
	if config.Verbose {
		fmt.Println("🚀 Starting curl.sh generation...")
	}

	// Generate comprehensive test cases using CategoryMatrix
	cm := testcases.NewCategoryMatrix()

	// Create curl.sh script
	if err := generateCurlScriptFromSpecs(cm.TestCases, config); err != nil {
		return fmt.Errorf("failed to generate curl.sh: %w", err)
	}

	if config.Verbose {
		fmt.Printf("✅ Generated curl.sh script with %d test cases\n", len(cm.TestCases))
	}

	return nil
}





// GetRecordCounts returns current user and account counts via API calls, paging through all data
func GetRecordCounts(config Config) (int, int, error) {
	serverURL := config.ServerURL
	if serverURL == "" {
		serverURL = "http://localhost:5500"
	}

	// Count users by paging through all data 10 at a time
	userCount, err := countRecordsByPaging(serverURL, "/api/User", config.Verbose)
	if err != nil {
		return 0, 0, fmt.Errorf("failed to count users: %w", err)
	}

	// Count accounts by paging through all data 10 at a time
	accountCount, err := countRecordsByPaging(serverURL, "/api/Account", config.Verbose)
	if err != nil {
		return 0, 0, fmt.Errorf("failed to count accounts: %w", err)
	}

	return userCount, accountCount, nil
}

// getAllRecordsByPaging pages through API data 10 records at a time and returns all IDs
func getAllRecordsByPaging(serverURL, endpoint string, verbose bool) ([]string, error) {
	var allIDs []string
	page := 1
	pageSize := 10

	for {
		// Build URL with pagination parameters
		url := fmt.Sprintf("%s%s?page=%d&pageSize=%d", serverURL, endpoint, page, pageSize)

		if verbose {
			fmt.Printf("  📄 Fetching %s page %d...\n", endpoint, page)
		}

		resp, err := http.Get(url)
		if err != nil {
			return nil, fmt.Errorf("failed to fetch page %d: %w", page, err)
		}
		defer resp.Body.Close()

		if resp.StatusCode != 200 {
			return nil, fmt.Errorf("server error on page %d: %d", page, resp.StatusCode)
		}

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to read page %d response: %w", page, err)
		}

		var response map[string]interface{}
		if err := json.Unmarshal(body, &response); err != nil {
			return nil, fmt.Errorf("failed to parse page %d response: %w", page, err)
		}

		// Extract IDs from this page
		pageCount := 0
		if data, ok := response["data"].([]interface{}); ok {
			for _, item := range data {
				if record, ok := item.(map[string]interface{}); ok {
					if id, ok := record["id"].(string); ok {
						allIDs = append(allIDs, id)
					}
				}
			}
			pageCount = len(data)
		}

		if verbose {
			fmt.Printf("    ✓ Page %d: %d records (total so far: %d)\n", page, pageCount, len(allIDs))
		}

		// Check if we have pagination info to determine if there are more pages
		if pagination, ok := response["pagination"].(map[string]interface{}); ok {
			if totalPages, ok := pagination["totalPages"].(float64); ok {
				if page >= int(totalPages) {
					break // No more pages
				}
			} else {
				// No totalPages field, check if we got less than pageSize records
				if pageCount < pageSize {
					break // Last page
				}
			}
		} else {
			// No pagination info, check if we got less than pageSize records
			if pageCount < pageSize {
				break // Last page
			}
		}

		page++
	}

	return allIDs, nil
}

// countRecordsByPaging pages through API data 10 records at a time and returns total count
func countRecordsByPaging(serverURL, endpoint string, verbose bool) (int, error) {
	ids, err := getAllRecordsByPaging(serverURL, endpoint, verbose)
	if err != nil {
		return 0, err
	}
	return len(ids), nil
}

// EnsureMinRecords ensures minimum number of users and accounts exist
func EnsureMinRecords(config Config, recordSpec string) error {
	// Parse "users,accounts" format
	parts := strings.Split(recordSpec, ",")
	if len(parts) != 2 {
		return fmt.Errorf("invalid format for records, expected 'users,accounts' got '%s'", recordSpec)
	}

	minUsers, err := strconv.Atoi(strings.TrimSpace(parts[0]))
	if err != nil {
		return fmt.Errorf("invalid user count '%s': %w", parts[0], err)
	}

	minAccounts, err := strconv.Atoi(strings.TrimSpace(parts[1]))
	if err != nil {
		return fmt.Errorf("invalid account count '%s': %w", parts[1], err)
	}

	if config.Verbose {
		fmt.Printf("🔍 Ensuring minimum records: %d users, %d accounts\n", minUsers, minAccounts)
	}

	// Get current counts
	currentUsers, currentAccounts, err := GetRecordCounts(config)
	if err != nil {
		return fmt.Errorf("failed to get current record counts: %w", err)
	}

	if config.Verbose {
		fmt.Printf("📊 Current records: %d users, %d accounts\n", currentUsers, currentAccounts)
	}

	// Calculate how many we need to create
	needUsers := max(0, minUsers-currentUsers)
	needAccounts := max(0, minAccounts-currentAccounts)

	if needUsers == 0 && needAccounts == 0 {
		if config.Verbose {
			fmt.Printf("✅ Already have minimum records: %d users, %d accounts\n", currentUsers, currentAccounts)
		}
		return nil
	}

	if config.Verbose {
		fmt.Printf("➕ Creating %d additional accounts and %d additional users\n", needAccounts, needUsers)
	}

	// Create accounts first (users reference them)
	if needAccounts > 0 {
		if err := createAccountsViaAPI(config, needAccounts); err != nil {
			return fmt.Errorf("failed to create accounts: %w", err)
		}
	}

	// Create users
	if needUsers > 0 {
		if err := createUsersViaAPI(config, needUsers); err != nil {
			return fmt.Errorf("failed to create users: %w", err)
		}
	}

	if config.Verbose {
		fmt.Printf("✅ Successfully ensured minimum records: %d users, %d accounts\n", minUsers, minAccounts)
	}

	return nil
}

// createAccountsViaAPI creates accounts via REST API calls
func createAccountsViaAPI(config Config, count int) error {
	serverURL := config.ServerURL
	if serverURL == "" {
		serverURL = "http://localhost:5500"
	}

	for i := 0; i < count; i++ {
		account := generateRandomAccountData(fmt.Sprintf("gen_account_%d_%d", time.Now().Unix(), i))

		jsonData, err := json.Marshal(account)
		if err != nil {
			return fmt.Errorf("failed to marshal account data: %w", err)
		}

		resp, err := http.Post(serverURL+"/api/Account", "application/json", bytes.NewBuffer(jsonData))
		if err != nil {
			return fmt.Errorf("failed to create account %d: %w", i+1, err)
		}

		if resp.StatusCode != 200 && resp.StatusCode != 201 {
			// Read the response body to see the error details
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			return fmt.Errorf("server error creating account %d: %d - Payload: %s - Response: %s", i+1, resp.StatusCode, string(jsonData), string(body))
		}
		resp.Body.Close()

		if config.Verbose {
			fmt.Printf("  ✓ Created account %s\n", account["id"])
		}
	}

	return nil
}

// createUsersViaAPI creates users via REST API calls
func createUsersViaAPI(config Config, count int) error {
	serverURL := config.ServerURL
	if serverURL == "" {
		serverURL = "http://localhost:5500"
	}

	// Get some account IDs to use for FK relationships
	_, _, err := GetRecordCounts(config)
	if err != nil {
		return fmt.Errorf("failed to verify accounts exist: %w", err)
	}

	for i := 0; i < count; i++ {
		user := generateRandomUserData(fmt.Sprintf("gen_user_%d_%d", time.Now().Unix(), i))

		jsonData, err := json.Marshal(user)
		if err != nil {
			return fmt.Errorf("failed to marshal user data: %w", err)
		}

		resp, err := http.Post(serverURL+"/api/User", "application/json", bytes.NewBuffer(jsonData))
		if err != nil {
			return fmt.Errorf("failed to create user %d: %w", i+1, err)
		}

		if resp.StatusCode != 200 && resp.StatusCode != 201 {
			// Read the response body to see the error details
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			return fmt.Errorf("server error creating user %d: %d - Payload: %s - Response: %s", i+1, resp.StatusCode, string(jsonData), string(body))
		}
		resp.Body.Close()

		if config.Verbose {
			fmt.Printf("  ✓ Created user %s\n", user["id"])
		}
	}

	return nil
}

// generateRandomAccountData creates account data for API calls
func generateRandomAccountData(id string) map[string]interface{} {
	now := time.Now().UTC()
	return map[string]interface{}{
		"id":        id,
		"name":      fmt.Sprintf("Generated Account %s", id),
		"createdAt": now.Format(time.RFC3339),
		"updatedAt": now.Format(time.RFC3339),
	}
}

// generateRandomUserData creates user data for API calls
func generateRandomUserData(id string) map[string]interface{} {
	now := time.Now().UTC()
	genders := []string{"male", "female", "other"}

	return map[string]interface{}{
		"id":             id,
		"username":       id,
		"email":          fmt.Sprintf("%s@generated.com", id),
		"firstName":      "Generated",
		"lastName":       "User",
		"password":       "GeneratedPass123!",
		"accountId":      "primary_valid_001", // Use a known good account ID
		"gender":         genders[len(id)%len(genders)],
		"netWorth":       float64((len(id)%100 + 1) * 1000),
		"isAccountOwner": len(id)%2 == 0,
		"dob":            time.Date(1980+(len(id)%30), time.Month((len(id)%12)+1), (len(id)%28)+1, 0, 0, 0, 0, time.UTC).Format(time.RFC3339),
		"createdAt":      now.Format(time.RFC3339),
		"updatedAt":      now.Format(time.RFC3339),
	}
}


// CleanDatabase cleans all data via REST API using pagination
func CleanDatabase(config Config) error {
	serverURL := config.ServerURL
	if serverURL == "" {
		serverURL = "http://localhost:5500"
	}

	if config.Verbose {
		fmt.Println("🧹 Cleaning database via API...")
	}

	// Get all user IDs using pagination
	userIDs, err := getAllRecordsByPaging(serverURL, "/api/User", config.Verbose)
	if err != nil {
		return fmt.Errorf("failed to get user IDs for deletion: %w", err)
	}

	// Delete all users
	client := &http.Client{}
	for _, userID := range userIDs {
		req, err := http.NewRequest("DELETE", serverURL+"/api/User/"+userID, nil)
		if err != nil {
			if config.Verbose {
				fmt.Printf("  ✗ Failed to create delete request for user %s: %v\n", userID, err)
			}
			continue
		}
		resp, err := client.Do(req)
		if err != nil {
			if config.Verbose {
				fmt.Printf("  ✗ Failed to delete user %s: %v\n", userID, err)
			}
			continue
		}
		resp.Body.Close()
		if config.Verbose {
			fmt.Printf("  ✓ Deleted user %s\n", userID)
		}
	}

	// Get all account IDs using pagination
	accountIDs, err := getAllRecordsByPaging(serverURL, "/api/Account", config.Verbose)
	if err != nil {
		return fmt.Errorf("failed to get account IDs for deletion: %w", err)
	}

	// Delete all accounts
	for _, accountID := range accountIDs {
		req, err := http.NewRequest("DELETE", serverURL+"/api/Account/"+accountID, nil)
		if err != nil {
			if config.Verbose {
				fmt.Printf("  ✗ Failed to create delete request for account %s: %v\n", accountID, err)
			}
			continue
		}
		resp, err := client.Do(req)
		if err != nil {
			if config.Verbose {
				fmt.Printf("  ✗ Failed to delete account %s: %v\n", accountID, err)
			}
			continue
		}
		resp.Body.Close()
		if config.Verbose {
			fmt.Printf("  ✓ Deleted account %s\n", accountID)
		}
	}

	if config.Verbose {
		fmt.Printf("✅ Database cleaning completed: deleted %d users, %d accounts\n", len(userIDs), len(accountIDs))
	}

	return nil
}


// generateCurlScriptFromSpecs creates curl.sh from test specifications
func generateCurlScriptFromSpecs(testSpecs []testcases.TestSpec, config Config) error {
	file, err := os.Create("curl.sh")
	if err != nil {
		return fmt.Errorf("failed to create curl.sh: %w", err)
	}
	defer file.Close()

	serverURL := config.ServerURL
	if serverURL == "" {
		serverURL = "http://localhost:5500"
	}

	// Write curl script header
	header := fmt.Sprintf(`#!/bin/bash
# Generated curl commands from comprehensive test execution
# Auto-generated by data generation tool

# Function to execute a URL and output structured JSON
execute_url() {
    local method="$1"
    local url="$2"
    local description="$3"
    local category="$4"

    # Execute curl and capture full response with status
    local full_response=$(curl -s -w "\nSTATUS:%%{http_code}" -X "$method" "$url")
    local response_body=$(echo "$full_response" | sed '$d')  # Remove last line (status)
    local status=$(echo "$full_response" | tail -n 1 | sed 's/STATUS://')  # Extract status code
    local timestamp=$(date -u +"%%Y-%%m-%%dT%%H:%%M:%%S.%%3NZ")

    # Output as key-value pair with URL as key
    local url_path=$(echo "$url" | sed 's|^http[s]*://[^/]*||')
    echo "  \"$url_path\": {"
    echo "    \"method\": \"$method\","
    echo "    \"description\": \"$description\","
    echo "    \"category\": \"$category\","
    echo "    \"status\": $((status)),"
    echo "    \"timestamp\": \"$timestamp\","

    # Check if response_body is valid JSON, if not quote it as string
    if echo "$response_body" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        echo "    \"response\": $response_body"
    else
        # Escape quotes and wrap in JSON string
        local escaped_response=$(echo "$response_body" | sed 's/"/\\"/g')
        echo "    \"response\": \"$escaped_response\""
    fi
    echo "  },"
}

# Wrap all output in object braces and fix trailing comma
(
echo "{"

`)

	if _, err := file.WriteString(header); err != nil {
		return fmt.Errorf("failed to write header: %w", err)
	}

	// Group tests by category and write them
	categories := map[string][]testcases.TestSpec{}
	categoryOrder := []string{"basic", "view", "view_individual", "view_combo", "page", "filter", "sort", "case", "invalid", "combo"}

	for _, spec := range testSpecs {
		categories[spec.Category] = append(categories[spec.Category], spec)
	}

	// Write tests by category
	for _, category := range categoryOrder {
		specs, exists := categories[category]
		if !exists {
			continue
		}

		categoryName := map[string]string{
			"basic":           "Basic API Tests",
			"view":            "View Parameter Tests",
			"view_individual": "Individual User + View Edge Cases",
			"view_combo":      "View + Parameter Combinations",
			"page":            "Pagination Tests",
			"filter":          "Filtering Tests",
			"sort":            "Sorting Tests",
			"case":            "Case Sensitivity Tests",
			"invalid":         "Invalid Field Tests",
			"combo":           "Complex Parameter Combinations",
		}[category]

		if _, err := file.WriteString(fmt.Sprintf("# ========== %s ==========\n", categoryName)); err != nil {
			return err
		}

		for _, spec := range specs {
			if _, err := file.WriteString(fmt.Sprintf("execute_url \"%s\" \"%s%s\" \"%s\" \"%s\"\n",
				spec.Method, serverURL, spec.URL, spec.Description, spec.Category)); err != nil {
				return err
			}
		}
	}

	// Write footer
	footer := `
# Close JSON object (remove trailing comma and add closing brace)
) | sed '$s/,$/}/'
`
	if _, err := file.WriteString(footer); err != nil {
		return err
	}

	return nil
}

// Helper function for max of two integers
func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}