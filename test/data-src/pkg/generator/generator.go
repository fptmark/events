package generator

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"data-generator/pkg/testcases"
	"events-shared/schema"
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

// EnsureStaticTestData ensures static test accounts and users exist for test cases
func EnsureStaticTestData(config Config) error {
	serverURL := config.ServerURL
	if serverURL == "" {
		serverURL = "http://localhost:5500"
	}

	if config.Verbose {
		fmt.Println("🔧 Ensuring static test data exists...")
	}

	// Create the primary static account that all valid FK tests reference
	staticAccount := map[string]interface{}{
		"id":        "primary_valid_001",
		"name":      "Primary Test Account",
		"createdAt": time.Now().UTC().Format(time.RFC3339),
		"updatedAt": time.Now().UTC().Format(time.RFC3339),
	}

	jsonData, err := json.Marshal(staticAccount)
	if err != nil {
		return fmt.Errorf("failed to marshal static account: %w", err)
	}

	// Try to create the account (ignore if it already exists)
	resp, err := http.Post(serverURL+"/api/Account", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create static account: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 || resp.StatusCode == 201 {
		if config.Verbose {
			fmt.Printf("  ✓ Created static account: primary_valid_001\n")
		}
	} else if resp.StatusCode == 409 || resp.StatusCode == 400 {
		// Account already exists, which is fine
		if config.Verbose {
			fmt.Printf("  ✓ Static account already exists: primary_valid_001\n")
		}
	} else {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to create static account: status %d - %s", resp.StatusCode, string(body))
	}

	return nil
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

		resp, err := http.Post(serverURL+"/api/User?novalidate", "application/json", bytes.NewBuffer(jsonData))
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

// Random data pools for generating varied test data
var (
	firstNames = []string{
		"James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
		"William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
		"Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa",
		"Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna",
		"Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle",
		"Kenneth", "Laura", "Kevin", "Sarah", "Brian", "Kimberly", "George", "Deborah",
	}

	lastNames = []string{
		"Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
		"Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
		"Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
		"Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
		"Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
		"Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
	}

	emailDomains = []string{
		"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "company.com",
		"business.org", "test.net", "example.com", "mail.com", "email.co",
	}
)

// generateRandomString creates a random string of specified length
func generateRandomString(r *rand.Rand, length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	result := make([]byte, length)
	for i := range result {
		result[i] = charset[r.Intn(len(charset))]
	}
	return string(result)
}

// generateRandomUserData creates user data for API calls using schema constraints
func generateRandomUserData(id string) map[string]interface{} {
	now := time.Now().UTC()

	// Create a more varied random source using current time and ID
	source := rand.NewSource(time.Now().UnixNano() + int64(len(id)))
	r := rand.New(source)

	// Try to load schema for constraints
	var schemaCache *schema.SchemaCache
	if schemaPath, err := schema.FindSchemaFile(); err == nil {
		if cache, err := schema.NewSchemaCache(schemaPath); err == nil {
			schemaCache = cache
		}
	}

	// Generate username with constraints (min: 3, max: 50)
	username := generateConstrainedString(r, schemaCache, "User", "username", strings.ToLower(firstNames[r.Intn(len(firstNames))]))

	// Generate email with constraints (min: 8, max: 50)
	firstName := firstNames[r.Intn(len(firstNames))]
	lastName := lastNames[r.Intn(len(lastNames))]
	emailDomain := emailDomains[r.Intn(len(emailDomains))]
	baseEmail := fmt.Sprintf("%s.%s@%s", strings.ToLower(firstName), strings.ToLower(lastName), emailDomain)
	email := generateConstrainedString(r, schemaCache, "User", "email", baseEmail)

	// Generate firstName with constraints (min: 3, max: 100)
	firstName = generateConstrainedString(r, schemaCache, "User", "firstName", firstName)

	// Generate lastName with constraints (min: 3, max: 100)
	lastName = generateConstrainedString(r, schemaCache, "User", "lastName", lastName)

	// Generate password with constraints (min: 8)
	password := generateConstrainedString(r, schemaCache, "User", "password", "TestPass"+generateRandomString(r, 6)+"!")

	// Generate gender from enum constraints
	gender := generateConstrainedEnum(r, schemaCache, "User", "gender", []string{"male", "female", "other"})

	// Generate netWorth with numeric constraints (ge: 0, le: 10000000)
	netWorth := generateConstrainedNumber(r, schemaCache, "User", "netWorth", 0, 10000000)

	// Calculate birth year range (current year - 65 to current year - 25)
	currentYear := now.Year()
	minBirthYear := currentYear - 65
	maxBirthYear := currentYear - 25

	// Generate random birth date
	birthYear := minBirthYear + r.Intn(maxBirthYear-minBirthYear+1)
	birthMonth := time.Month(r.Intn(12) + 1)
	birthDay := r.Intn(28) + 1 // Use 28 to avoid month-specific day issues

	dob := time.Date(birthYear, birthMonth, birthDay, 0, 0, 0, 0, time.UTC)

	return map[string]interface{}{
		"id":             id,
		"username":       username,
		"email":          email,
		"firstName":      firstName,
		"lastName":       lastName,
		"password":       password,
		"accountId":      "primary_valid_001", // Use a known good account ID
		"gender":         gender,
		"netWorth":       netWorth,
		"isAccountOwner": r.Intn(2) == 0, // 50/50 chance
		"dob":            dob.Format(time.RFC3339),
		"createdAt":      now.Format(time.RFC3339),
		"updatedAt":      now.Format(time.RFC3339),
	}
}

// generateConstrainedString generates a string respecting schema length constraints
func generateConstrainedString(r *rand.Rand, schemaCache *schema.SchemaCache, entityType, fieldName, baseValue string) string {
	if schemaCache == nil {
		return baseValue
	}

	constraints, exists := schemaCache.GetFieldConstraints(entityType, fieldName)
	if !exists {
		return baseValue
	}

	// Ensure minimum length
	if constraints.MinLength != nil && len(baseValue) < *constraints.MinLength {
		// Pad with random characters
		needed := *constraints.MinLength - len(baseValue)
		baseValue += generateRandomString(r, needed)
	}

	// Ensure maximum length
	if constraints.MaxLength != nil && len(baseValue) > *constraints.MaxLength {
		// Truncate but keep it meaningful
		if *constraints.MaxLength > 3 {
			baseValue = baseValue[:*constraints.MaxLength-3] + "..."
		} else {
			baseValue = baseValue[:*constraints.MaxLength]
		}
	}

	return baseValue
}

// generateConstrainedEnum generates a value from enum constraints
func generateConstrainedEnum(r *rand.Rand, schemaCache *schema.SchemaCache, entityType, fieldName string, defaultValues []string) string {
	if schemaCache == nil {
		return defaultValues[r.Intn(len(defaultValues))]
	}

	constraints, exists := schemaCache.GetFieldConstraints(entityType, fieldName)
	if !exists || constraints.Enum == nil || len(constraints.Enum.Values) == 0 {
		return defaultValues[r.Intn(len(defaultValues))]
	}

	return constraints.Enum.Values[r.Intn(len(constraints.Enum.Values))]
}

// generateConstrainedNumber generates a number respecting schema numeric constraints
func generateConstrainedNumber(r *rand.Rand, schemaCache *schema.SchemaCache, entityType, fieldName string, defaultMin, defaultMax float64) float64 {
	min := defaultMin
	max := defaultMax

	if schemaCache != nil {
		if constraints, exists := schemaCache.GetFieldConstraints(entityType, fieldName); exists {
			if constraints.Ge != nil {
				min = *constraints.Ge
			}
			if constraints.Le != nil {
				max = *constraints.Le
			}
		}
	}

	// Generate random value within range
	if max > min {
		return min + r.Float64()*(max-min)
	}
	return min
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
