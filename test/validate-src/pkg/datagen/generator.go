package datagen

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"strconv"
	"strings"
	"time"

	"events-shared/schema"
)

// TestCategory represents a test category
type TestCategory struct {
	Name        string
	Description string
}

// Config holds configuration for data generation
type Config struct {
	ServerURL string `json:"server_url,omitempty"` // API server URL, defaults to localhost:5500
	Verbose   bool   `json:"-"`                    // Not from config file
}

// Global config instance
var GlobalConfig Config

func SetConfigDefaults(serverURL string, verbose bool) {
	GlobalConfig.ServerURL = serverURL
	GlobalConfig.Verbose = verbose
}

// GetRecordCounts returns current user and account counts via API calls, paging through all data
func GetRecordCounts(config Config) (int, int, error) {
	// Count users by paging through all data 10 at a time
	userCount, err := countRecordsByPaging("/api/User")
	if err != nil {
		return 0, 0, fmt.Errorf("failed to count users: %w", err)
	}

	// Count accounts by paging through all data 10 at a time
	accountCount, err := countRecordsByPaging("/api/Account")
	if err != nil {
		return 0, 0, fmt.Errorf("failed to count accounts: %w", err)
	}

	return userCount, accountCount, nil
}

// getAllRecordsByPaging pages through API data 10 records at a time and returns all IDs
func getAllRecordsByPaging(endpoint string) ([]string, error) {
	var allIDs []string
	page := 1
	pageSize := 10

	for {
		// Build URL with pagination parameters
		url := fmt.Sprintf("%s%s?page=%d&pageSize=%d", GlobalConfig.ServerURL, endpoint, page, pageSize)

		if GlobalConfig.Verbose {
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

		// DEBUG: Print raw response
		// fmt.Printf("DEBUG: URL=%s, Status=%d, BodyLen=%d\n", url, resp.StatusCode, len(body))
		// fmt.Printf("DEBUG: Raw body: %s\n", string(body))

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

		if GlobalConfig.Verbose {
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
func countRecordsByPaging(endpoint string) (int, error) {
	ids, err := getAllRecordsByPaging(endpoint)
	if err != nil {
		return 0, err
	}
	return len(ids), nil
}

// EnsureStaticTestData ensures static test accounts and users exist for test cases
func EnsureStaticTestData(config Config) error {
	if GlobalConfig.Verbose {
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
	resp, err := http.Post(GlobalConfig.ServerURL+"/api/Account", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create static account: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 || resp.StatusCode == 201 {
		if GlobalConfig.Verbose {
			fmt.Printf("  ✓ Created static account: primary_valid_001\n")
		}
	} else if resp.StatusCode == 409 || resp.StatusCode == 400 {
		// Account already exists, which is fine
		if GlobalConfig.Verbose {
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

	if GlobalConfig.Verbose {
		fmt.Printf("🔍 Ensuring minimum records: %d users, %d accounts\n", minUsers, minAccounts)
	}

	// Get current counts
	currentUsers, currentAccounts, err := GetRecordCounts(config)
	if err != nil {
		return fmt.Errorf("failed to get current record counts: %w", err)
	}

	if GlobalConfig.Verbose {
		fmt.Printf("📊 Current records: %d users, %d accounts\n", currentUsers, currentAccounts)
	}

	// Calculate how many we need to create
	needUsers := max(0, minUsers-currentUsers)
	needAccounts := max(0, minAccounts-currentAccounts)

	if needUsers == 0 && needAccounts == 0 {
		if GlobalConfig.Verbose {
			fmt.Printf("✅ Already have minimum records: %d users, %d accounts\n", currentUsers, currentAccounts)
		}
		return nil
	}

	if GlobalConfig.Verbose {
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
		if err := createUsers(config, needUsers, true, true); err != nil {
			return fmt.Errorf("failed to create users: %w", err)
		}
	}

	if GlobalConfig.Verbose {
		fmt.Printf("✅ Successfully ensured minimum records: %d users, %d accounts\n", minUsers, minAccounts)
	}

	return nil
}

// createAccountsViaAPI creates accounts via REST API calls
func createAccountsViaAPI(config Config, count int) error {
	for i := 0; i < count; i++ {
		account := generateRandomAccountData(fmt.Sprintf("gen_account_%d_%d", time.Now().Unix(), i))

		jsonData, err := json.Marshal(account)
		if err != nil {
			return fmt.Errorf("failed to marshal account data: %w", err)
		}

		resp, err := http.Post(GlobalConfig.ServerURL+"/api/Account", "application/json", bytes.NewBuffer(jsonData))
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

		if GlobalConfig.Verbose {
			fmt.Printf("  ✓ Created account %s\n", account["id"])
		}
	}

	return nil
}

// createUsers creates users via REST API calls
func createUsers(config Config, count int, valid_data bool, valid_account_id bool) error {
	accountIds := []string{}
	err := error(nil)

	// Get list of account IDs to use for FK relationships
	if valid_account_id {
		accountIds, err = getAllRecordsByPaging("/api/Account")
		if err != nil {
			return fmt.Errorf("failed to get account IDs: %w", err)
		}
		if len(accountIds) == 0 {
			return fmt.Errorf("no accounts available for user creation")
		}
	} else {
		// Use some invalid account IDs for testing
		accountIds = []string{"invalid_acc_001", "invalid_acc_002", "invalid_acc_003"}
	}

	for i := 0; i < count; i++ {
		// Round-robin assign account ID
		accountID := accountIds[i%len(accountIds)]
		user := generateRandomUserDataWithAccountID(fmt.Sprintf("gen_user_%d_%d", time.Now().Unix(), i), accountID, valid_data)

		jsonData, err := json.Marshal(user)
		if err != nil {
			return fmt.Errorf("failed to marshal user data: %w", err)
		}

		url := GlobalConfig.ServerURL + "/api/User"
		if !valid_data || !valid_account_id {
			url += "?novalidate"
		}
		resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
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

		if GlobalConfig.Verbose {
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

// generateRandomUserDataWithAccountID creates user data for API calls with specified account ID
func generateRandomUserDataWithAccountID(id string, accountID string, valid_data bool) map[string]interface{} {
	userData := generateRandomUserData(id, valid_data)
	userData["accountId"] = accountID
	return userData
}

// generateRandomUserData creates user data for API calls using schema constraints
func generateRandomUserData(id string, valid_data bool) map[string]interface{} {
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

	userData := map[string]interface{}{
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

	// If valid_data is false, introduce random violations
	if !valid_data {
		userData = introduceRandomViolations(r, userData)
	}

	return userData
}

// introduceRandomViolations randomly violates field constraints to generate invalid test data
func introduceRandomViolations(r *rand.Rand, userData map[string]interface{}) map[string]interface{} {
	// List of fields that can be violated and their violation strategies
	violationStrategies := []func(*rand.Rand, map[string]interface{}){
		violateUsername,
		violateEmail,
		violateFirstName,
		violateLastName,
		violatePassword,
		violateGender,
		violateNetWorth,
		violateDob,
	}

	// Randomly pick 1-3 violations to apply
	numViolations := r.Intn(3) + 1
	appliedViolations := make(map[int]bool)

	for i := 0; i < numViolations; i++ {
		// Pick a random violation strategy that hasn't been used yet
		violationIndex := r.Intn(len(violationStrategies))
		for appliedViolations[violationIndex] {
			violationIndex = r.Intn(len(violationStrategies))
		}
		appliedViolations[violationIndex] = true

		// Apply the violation
		violationStrategies[violationIndex](r, userData)
	}

	return userData
}

// violateUsername introduces violations in username field
func violateUsername(r *rand.Rand, userData map[string]interface{}) {
	violations := []string{
		"x",                     // Too short (min: 3)
		strings.Repeat("a", 55), // Too long (max: 50)
		"",                      // Empty string
		"  ",                    // Just spaces
		"user with spaces",      // Invalid characters
		"user@invalid",          // Special characters
	}
	userData["username"] = violations[r.Intn(len(violations))]
}

// violateEmail introduces violations in email field
func violateEmail(r *rand.Rand, userData map[string]interface{}) {
	violations := []string{
		"a@b.c",                            // Too short (min: 8)
		strings.Repeat("a", 45) + "@b.com", // Too long (max: 50)
		"",                                 // Empty string
		"notanemail",                       // Invalid format
		"user@",                            // Incomplete
		"@domain.com",                      // Missing user part
		"user@.com",                        // Invalid domain
		"user space@domain.com",            // Spaces in email
	}
	userData["email"] = violations[r.Intn(len(violations))]
}

// violateFirstName introduces violations in firstName field
func violateFirstName(r *rand.Rand, userData map[string]interface{}) {
	violations := []string{
		"A",                      // Too short (min: 3)
		strings.Repeat("A", 105), // Too long (max: 100)
		"",                       // Empty string
		"  ",                     // Just spaces
		"123",                    // Numbers only
		"Fi!",                    // Special characters
	}
	userData["firstName"] = violations[r.Intn(len(violations))]
}

// violateLastName introduces violations in lastName field
func violateLastName(r *rand.Rand, userData map[string]interface{}) {
	violations := []string{
		"L",                      // Too short (min: 3)
		strings.Repeat("L", 105), // Too long (max: 100)
		"",                       // Empty string
		"  ",                     // Just spaces
		"456",                    // Numbers only
		"La$t",                   // Special characters
	}
	userData["lastName"] = violations[r.Intn(len(violations))]
}

// violatePassword introduces violations in password field
func violatePassword(r *rand.Rand, userData map[string]interface{}) {
	violations := []string{
		"123",     // Too short (min: 8)
		"",        // Empty string
		"       ", // Just spaces
		"1234567", // 7 chars (one less than min)
	}
	userData["password"] = violations[r.Intn(len(violations))]
}

// violateGender introduces violations in gender field
func violateGender(r *rand.Rand, userData map[string]interface{}) {
	violations := []string{
		"invalid", // Not in enum
		"MALE",    // Wrong case
		"man",     // Different value
		"",        // Empty string
		"both",    // Not in enum
		"unknown", // Not in enum
	}
	userData["gender"] = violations[r.Intn(len(violations))]
}

// violateNetWorth introduces violations in netWorth field
func violateNetWorth(r *rand.Rand, userData map[string]interface{}) {
	violations := []interface{}{
		-100.50,        // Negative (ge: 0)
		15000000.75,    // Too high (le: 10000000)
		"not_a_number", // Invalid type
		-1,             // Negative integer
		10000001,       // Just over limit
	}
	userData["netWorth"] = violations[r.Intn(len(violations))]
}

// violateDob introduces violations in dob field
func violateDob(r *rand.Rand, userData map[string]interface{}) {
	violations := []string{
		"not-a-date",           // Invalid format
		"2025-12-01T00:00:00Z", // Future date
		"1800-01-01T00:00:00Z", // Too old
		"invalid",              // Invalid string
		"",                     // Empty string
		"01/01/2000",           // Wrong format
	}
	userData["dob"] = violations[r.Intn(len(violations))]
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

// CleanDatabase cleans all data via the db/init/confirmed endpoint
func CleanDatabase(config Config) error {
	if GlobalConfig.Verbose {
		fmt.Println("🧹 Cleaning database via API...")
	}

	client := &http.Client{}
	req, err := http.NewRequest("POST", GlobalConfig.ServerURL+"/api/db/init/confirmed", nil)
	if err != nil {
		return fmt.Errorf("failed to create database init request: %w", err)
	}

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to call database init endpoint: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("database init failed with status %d: %s", resp.StatusCode, string(body))
	}

	if GlobalConfig.Verbose {
		fmt.Println("✅ Database cleaning completed via /api/db/init/confirmed")
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

// ResetAndPopulate performs the complete database reset and population sequence using working data-src code
func ResetAndPopulate(serverURL string, userCount, accountCount int) error {
	config := Config{
		ServerURL: serverURL,
		Verbose:   true,
	}

	// Step 1: Get initial counts
	fmt.Println("Getting initial database counts...")
	initialUsers, initialAccounts, err := GetRecordCounts(config)
	if err != nil {
		return fmt.Errorf("failed to get initial record counts: %w", err)
	}
	fmt.Printf("Initial counts: %d users, %d accounts\n", initialUsers, initialAccounts)

	// Step 2: Clear database using the working CleanDatabase function
	fmt.Println("Clearing database...")
	if err := CleanDatabase(config); err != nil {
		return fmt.Errorf("failed to clear database: %w", err)
	}

	// Step 3: Get counts after clearing
	fmt.Println("Getting database counts after clearing...")
	afterUsers, afterAccounts, err := GetRecordCounts(config)
	if err != nil {
		return fmt.Errorf("failed to get record counts after clearing: %w", err)
	}
	fmt.Printf("After clearing: %d users, %d accounts\n", afterUsers, afterAccounts)

	// Step 4: Populate with specified counts using the working EnsureMinRecords function
	fmt.Printf("Populating database with %d users and %d accounts...\n", userCount, accountCount)
	recordSpec := fmt.Sprintf("%d,%d", userCount, accountCount)
	if err := EnsureMinRecords(config, recordSpec); err != nil {
		return fmt.Errorf("failed to populate database: %w", err)
	}

	// Step 5: Get final counts
	fmt.Println("Getting final database counts...")
	finalUsers, finalAccounts, err := GetRecordCounts(config)
	if err != nil {
		return fmt.Errorf("failed to get final record counts: %w", err)
	}
	fmt.Printf("Final counts: %d users, %d accounts\n", finalUsers, finalAccounts)

	fmt.Println("Database reset and population complete!")
	return nil
}
