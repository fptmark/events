package datagen

import (
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"strings"
	"time"
	"validate/pkg/core"

	"events-shared/schema"
)

// TestCategory represents a test category
type TestCategory struct {
	Name        string
	Description string
}

// CreateTestData creates static test accounts and users for test cases
// Accounts will be account_1, account_2, etc.
// Users will be user_1, user_2, etc. with username <firstname>_<lastname>_xx
func CreateTestData(numAccounts int, numUsers int) error {
	if core.Verbose {
		fmt.Println("🔧 Creating test data...")
	}

	// Generate random number for domain variability (1 to max accounts)
	y := rand.Intn(numAccounts) + 1

	// Create accounts
	for i := 1; i <= numAccounts; i++ {
		accountID := fmt.Sprintf("account_%d", i)
		account := map[string]interface{}{
			"id":        accountID,
			"createdAt": time.Now().UTC().Format(time.RFC3339),
			"updatedAt": time.Now().UTC().Format(time.RFC3339),
		}

		if err := core.CreateEntity("Account", account); err != nil {
			return fmt.Errorf("failed to create account %s: %w", accountID, err)
		}

		if core.Verbose {
			fmt.Printf("  ✓ Created account: %s\n", accountID)
		}
	}

	// Load schema for constraints
	var schemaCache *schema.SchemaCache
	if schemaPath, err := schema.FindSchemaFile(); err == nil {
		if cache, err := schema.NewSchemaCache(schemaPath); err == nil {
			schemaCache = cache
		}
	}

	// Create users (some with random violations for testing)
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	for i := 1; i <= numUsers; i++ {
		userID := fmt.Sprintf("user_%d", i)

		// Pick random first and last names
		firstName := firstNames[rand.Intn(len(firstNames))]
		lastName := lastNames[rand.Intn(len(lastNames))]

		// Apply schema constraints to names
		firstName = generateConstrainedString(r, schemaCache, "User", "firstName", firstName)
		lastName = generateConstrainedString(r, schemaCache, "User", "lastName", lastName)

		// Username is <firstname>_<lastname>_xx with round-robin domain
		domain := emailDomains[(i-1)%len(emailDomains)]
		username := fmt.Sprintf("%s_%s_%s", firstName, lastName, domain)
		email := fmt.Sprintf("%s@%s", username, domain)

		// Account ID using round-robin with yy component
		accountID := fmt.Sprintf("account_%d", ((i-1)%y)+1)

		// Generate gender from schema enum
		gender := generateConstrainedEnum(r, schemaCache, "User", "gender", []string{"male", "female", "other"})

		// Generate netWorth with schema constraints
		netWorth := generateConstrainedNumber(r, schemaCache, "User", "netWorth", 0, 10000000)

		// Generate password with constraints
		password := generateConstrainedString(r, schemaCache, "User", "password", "TestPass"+generateRandomString(r, 6)+"!")

		user := map[string]interface{}{
			"id":             userID,
			"firstName":      firstName,
			"lastName":       lastName,
			"username":       username,
			"email":          email,
			"accountId":      accountID,
			"gender":         gender,
			"isAccountOwner": false,
			"netWorth":       netWorth,
			"dob":            "1990-01-01",
			"password":       password,
			"createdAt":      time.Now().UTC().Format(time.RFC3339),
			"updatedAt":      time.Now().UTC().Format(time.RFC3339),
		}

		if err := core.CreateEntity("User", user); err != nil {
			return fmt.Errorf("failed to create user %s: %w", userID, err)
		}

		if core.Verbose {
			fmt.Printf("  ✓ Created user: %s (username: %s, account: %s)\n", userID, username, accountID)
		}
	}

	return nil
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
func CleanDatabase() error {
	if core.Verbose {
		fmt.Println("🧹 Cleaning database via API...")
	}

	client := &http.Client{}
	req, err := http.NewRequest("POST", core.ServerURL+"/api/db/init/confirmed", nil)
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

	if core.Verbose {
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

// ResetAndPopulate performs the complete database reset and population sequence
func ResetAndPopulate(numUsers, numAccounts int) error {
	if err := CleanDatabase(); err != nil {
		return fmt.Errorf("failed to clean database: %w", err)
	}

	if err := CreateTestData(numAccounts, numUsers); err != nil {
		return fmt.Errorf("failed to create test data: %w", err)
	}

	return nil
}
