package tests

import (
	"fmt"
	"hash/fnv"
	"strings"
	"time"

	"validate/pkg/core"
	"validate/pkg/types"
)

// Data arrays for fixture generation (shared with random.go)
var (
	genders = []string{"male", "female", "other"}

	// netWorth values array for variety (within schema range 0-10000000)
	netWorthValues = []float64{
		0, 15000, 25000, 35000, 50000, 75000, 100000, 150000, 250000, 500000,
		750000, 1000000, 2500000, 5000000, 10000000,
	}

	// Birth years for DOB generation (variety of ages)
	birthYears = []int{
		1950, 1955, 1960, 1965, 1970, 1975, 1980, 1985, 1990, 1995, 2000, 2005,
	}

	birthMonths = []int{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}
	birthDays = []int{1, 5, 10, 15, 20, 25, 28}
)

// hashString returns a hash value for a string (used for deterministic array selection)
func hashString(s string) uint32 {
	h := fnv.New32a()
	h.Write([]byte(s))
	return h.Sum32()
}

// CreateFixtureAccount creates a test account with the given ID and optional field overrides
// Account schema: expiredAt (Date, optional), createdAt (auto), updatedAt (auto)
// ID convention: acc_{purpose}_{number}
//   Examples: acc_valid_001, acc_expired_001, acc_delete_001
func CreateFixtureAccount(id string, overrides map[string]interface{}) error {
	if core.Verbose {
		fmt.Printf("🔧 Creating fixture account: %s\n", id)
	}

	// Use hash of ID to determine if we include optional expiredAt
	hash := hashString(id)

	now := time.Now().UTC().Format(time.RFC3339)

	// Build account with required fields
	// Generate account name from ID
	accountName := fmt.Sprintf("Account %s", id)

	accountFields := map[string]interface{}{
		"id":        id,
		"name":      accountName,
		"createdAt": now,
		"updatedAt": now,
	}

	// Only include expireDate for some accounts (based on hash)
	if hash%3 == 0 {
		// Generate an expired date in the past for some accounts
		expiredDate := time.Now().AddDate(0, 0, -int(hash%365)).Format("2006-01-02")
		accountFields["expireDate"] = expiredDate
	}

	// Apply overrides
	for key, value := range overrides {
		accountFields[key] = value
	}

	// Use NewEntity to auto-populate required fields
	account, err := types.NewEntity("Account", accountFields)
	if err != nil {
		return fmt.Errorf("failed to create account entity %s: %w", id, err)
	}

	if err := core.CreateEntity("Account", account.ToJSON()); err != nil {
		return fmt.Errorf("failed to create fixture account %s: %w", id, err)
	}

	if core.Verbose {
		fmt.Printf("  ✓ Created fixture account: %s\n", id)
	}

	return nil
}

// CreateFixtureUser creates a test user with the given ID, accountId FK, and optional field overrides
// User schema per schema.yaml:
// - Required: username, email, password, firstName, lastName, isAccountOwner, accountId
// - Optional: gender, dob, netWorth
// ID convention: usr_{purpose}_{number}
//   Examples: usr_basic_001, usr_view_001, usr_nofk_001, usr_delete_001
//   For bulk random data: usr_r001, usr_r002, ... usr_rNNN
func CreateFixtureUser(id string, accountId string, overrides map[string]interface{}) error {
	if core.Verbose {
		fmt.Printf("🔧 Creating fixture user: %s\n", id)
	}

	// Use hash of ID to pick deterministic values from arrays
	hash := hashString(id)

	firstName := firstNames[hash%uint32(len(firstNames))]
	lastName := lastNames[(hash/2)%uint32(len(lastNames))]
	domain := emailDomains[hash%uint32(len(emailDomains))]

	username := fmt.Sprintf("%s_%s_%s", firstName, lastName, domain)
	email := fmt.Sprintf("%s.%s@%s", firstName, lastName, domain)

	// Generate valid password (min 8 chars from schema)
	password := fmt.Sprintf("Pass%d!", hash%10000)
	if len(password) < 8 {
		password = "Password123!"
	}

	now := time.Now().UTC().Format(time.RFC3339)

	// Build user with REQUIRED fields only
	userFields := map[string]interface{}{
		"id":             id,
		"firstName":      firstName,
		"lastName":       lastName,
		"username":       username,
		"email":          email,
		"password":       password,
		"isAccountOwner": (hash%2 == 0), // alternate true/false
		"accountId":      accountId,
		"createdAt":      now,
		"updatedAt":      now,
	}

	// OPTIONAL FIELDS - only include sometimes based on hash

	// Include gender ~66% of the time (hash % 3 != 0)
	if hash%3 != 0 {
		userFields["gender"] = genders[hash%uint32(len(genders))]
	}

	// Include dob ~50% of the time (hash % 2 == 0)
	if hash%2 == 0 {
		year := birthYears[hash%uint32(len(birthYears))]
		month := birthMonths[(hash/3)%uint32(len(birthMonths))]
		day := birthDays[(hash/5)%uint32(len(birthDays))]
		userFields["dob"] = fmt.Sprintf("%d-%02d-%02d", year, month, day)
	}

	// Include netWorth ~75% of the time (hash % 4 != 0)
	if hash%4 != 0 {
		userFields["netWorth"] = netWorthValues[hash%uint32(len(netWorthValues))]
	}

	// Apply overrides
	for key, value := range overrides {
		userFields[key] = value
	}

	// Use NewEntity to auto-populate required fields like roleId
	user, err := types.NewEntity("User", userFields)
	if err != nil {
		return fmt.Errorf("failed to create user entity %s: %w", id, err)
	}

	if err := core.CreateEntity("User", user.ToJSON()); err != nil {
		return fmt.Errorf("failed to create fixture user %s: %w", id, err)
	}

	if core.Verbose {
		fmt.Printf("  ✓ Created fixture user: %s (username: %s, account: %s)\n", id, username, accountId)
	}

	return nil
}

// parseEntityFromURL extracts entity type and ID from URL path
// Examples:
//   "/api/User/usr_basic_001" → ("User", "usr_basic_001")
//   "/api/Account/acc_valid_001" → ("Account", "acc_valid_001")
//   "/api/User" → ("User", "")
func parseEntityFromURL(url string) (entityType string, id string) {
	// Remove query params if present
	if idx := strings.Index(url, "?"); idx != -1 {
		url = url[:idx]
	}

	// Split path: /api/Entity/id
	parts := strings.Split(strings.Trim(url, "/"), "/")

	if len(parts) < 2 {
		return "", ""
	}

	entityType = parts[1] // "User" or "Account"

	if len(parts) >= 3 {
		id = parts[2] // "usr_basic_001" or "acc_valid_001"
	}

	return entityType, id
}

// getAccountIdFromRequestBody extracts accountId from RequestBody, or returns default
func getAccountIdFromRequestBody(requestBody map[string]interface{}) string {
	if requestBody == nil {
		return "acc_valid_001" // default
	}

	if accountId, exists := requestBody["accountId"]; exists {
		if accountIdStr, ok := accountId.(string); ok {
			return accountIdStr
		}
	}

	return "acc_valid_001" // default
}

// CreateFixturesFromTestCases creates fixtures for all test cases that need pre-existing entities
// This runs during ResetAndPopulate to ensure all fixtures exist before tests run
func CreateFixturesFromTestCases() error {
	if core.Verbose {
		fmt.Println("🔧 Creating fixtures from test cases...")
	}

	allTests := GetAllTestCases()
	createdAccounts := make(map[string]bool)
	createdUsers := make(map[string]bool)

	for _, testCase := range allTests {
		// Skip POST - they create entities during test execution
		if testCase.Method == "POST" {
			continue
		}

		// Skip if expecting 404 - entity shouldn't exist
		if testCase.ExpectedStatus == 404 {
			continue
		}

		// Extract entity type and ID from URL
		entityType, id := parseEntityFromURL(testCase.URL)
		if id == "" {
			continue // Collection endpoint like /api/User (no specific ID)
		}

		// Create fixture based on entity type
		if entityType == "User" {
			// Skip if already created
			if createdUsers[id] {
				continue
			}

			// Skip creating users with nonexist IDs (for FK validation tests)
			if strings.Contains(id, "nonexist") {
				continue
			}

			// Get accountId from RequestBody or use default
			accountId := getAccountIdFromRequestBody(testCase.RequestBody)

			// Skip creating accounts with nonexist IDs (for FK validation tests)
			if !strings.Contains(accountId, "nonexist") && !createdAccounts[accountId] {
				if err := CreateFixtureAccount(accountId, nil); err != nil {
					// Account might already exist, that's ok
					if core.Verbose {
						fmt.Printf("  ⚠ Account %s: %v\n", accountId, err)
					}
				} else {
					createdAccounts[accountId] = true
				}
			}

			// Create user with RequestBody as overrides
			if err := CreateFixtureUser(id, accountId, testCase.RequestBody); err != nil {
				return fmt.Errorf("failed to create user fixture %s: %w", id, err)
			}
			createdUsers[id] = true

		} else if entityType == "Account" {
			// Skip if already created
			if createdAccounts[id] {
				continue
			}

			// Skip creating accounts with nonexist IDs (for 404 tests)
			if strings.Contains(id, "nonexist") {
				continue
			}

			// Create account with RequestBody as overrides
			if err := CreateFixtureAccount(id, testCase.RequestBody); err != nil {
				return fmt.Errorf("failed to create account fixture %s: %w", id, err)
			}
			createdAccounts[id] = true
		}
	}

	// Create special test user for authentication tests
	authTestAccount := "acc_auth_001"
	if !createdAccounts[authTestAccount] {
		if err := CreateFixtureAccount(authTestAccount, nil); err != nil && core.Verbose {
			fmt.Printf("  ⚠ Account %s: %v\n", authTestAccount, err)
		} else {
			createdAccounts[authTestAccount] = true
		}
	}

	authTestUser := map[string]interface{}{
		"username":       "mark",
		"password":       "12345678",
		"email":          "mark@test.com",
		"firstName":      "Mark",
		"lastName":       "Test",
		"isAccountOwner": true,
	}
	if err := CreateFixtureUser("usr_auth_001", authTestAccount, authTestUser); err != nil && core.Verbose {
		fmt.Printf("  ⚠ Auth test user: %v\n", err)
	} else {
		createdUsers["usr_auth_001"] = true
	}

	if core.Verbose {
		fmt.Printf("✅ Created %d accounts and %d users from test cases\n", len(createdAccounts), len(createdUsers))
	}

	return nil
}
