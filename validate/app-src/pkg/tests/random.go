package tests

import (
	"fmt"
	"math/rand"
	"time"
	"validate/pkg/core"

	"events-shared/schema"
)

// CreateBulkData creates random bulk test accounts and users for get_all testing
// Accounts will be acc_r001, acc_r002, etc.
// Users will be usr_r001, usr_r002, etc. with random varied data
func CreateBulkData(numAccounts int, numUsers int) error {
	if core.Verbose {
		fmt.Println("🔧 Creating test data...")
	}

	// Generate random number for domain variability (1 to max accounts)
	y := rand.Intn(numAccounts) + 1

	// Create accounts with new ID convention: acc_r001, acc_r002, etc.
	for i := 1; i <= numAccounts; i++ {
		accountID := fmt.Sprintf("acc_r%03d", i)
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

	// Create users with new ID convention: usr_r001, usr_r002, etc.
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	for i := 1; i <= numUsers; i++ {
		userID := fmt.Sprintf("usr_r%03d", i)

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
		accountID := fmt.Sprintf("acc_r%03d", ((i-1)%y)+1)

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

// PopulateTestData creates all test data (bulk + fixtures)
// This is the populate function used by core.ResetAndPopulate
func PopulateTestData(numAccounts, numUsers int) error {
	// Step 1: Create bulk random data for get_all/sort/filter tests
	if err := CreateBulkData(numAccounts, numUsers); err != nil {
		return err
	}

	// Step 2: Create fixtures from test cases for specific CRUD tests
	if err := CreateFixturesFromTestCases(); err != nil {
		return err
	}

	return nil
}
