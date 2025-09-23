package testcases

import (
	"fmt"
	"time"

	"data-generator/pkg/models"
)

// TestSpec represents a single test case specification
type TestSpec struct {
	UserID      string
	AccountID   string
	URL         string
	Description string
	Method      string
	Category    string
}

// CategoryMatrix holds all test specifications organized by category
type CategoryMatrix struct {
	Accounts []models.Account
	Users    []models.User
	TestCases []TestSpec
}

// NewCategoryMatrix creates a comprehensive test matrix with all categories
func NewCategoryMatrix() *CategoryMatrix {
	cm := &CategoryMatrix{}

	// Create accounts first (users reference them)
	cm.generateCategoryAccounts()

	// Create users with category-specific naming and FK relationships
	cm.generateCategoryUsers()

	// Generate test case specifications
	cm.generateTestCases()

	return cm
}

// generateCategoryAccounts creates accounts for different test scenarios
func (cm *CategoryMatrix) generateCategoryAccounts() {
	now := time.Now().UTC()

	// Valid accounts for FK testing
	validAccounts := []models.Account{
		{
			ID:        "primary_valid_001",
			Name:      "Primary Test Account",
			CreatedAt: now,
			UpdatedAt: now,
			ExpiredAt: func() *time.Time { t := now.AddDate(1, 0, 0); return &t }(), // 1 year from now
		},
		{
			ID:        "primary_valid_002",
			Name:      "Secondary Test Account",
			CreatedAt: now,
			UpdatedAt: now,
			ExpiredAt: nil, // No expiration
		},
		{
			ID:        "primary_valid_003",
			Name:      "Tertiary Test Account",
			CreatedAt: now,
			UpdatedAt: now,
			ExpiredAt: func() *time.Time { t := now.AddDate(2, 0, 0); return &t }(), // 2 years from now
		},
	}

	// Invalid accounts for FK testing
	invalidAccounts := []models.Account{
		{
			ID:        "expired_invalid_001",
			Name:      "Expired Test Account",
			CreatedAt: now.AddDate(-1, 0, 0), // 1 year ago
			UpdatedAt: now,
			ExpiredAt: func() *time.Time { t := now.AddDate(0, -1, 0); return &t }(), // 1 month ago (expired)
		},
		{
			ID:        "expired_invalid_002",
			Name:      "Another Expired Account",
			CreatedAt: now.AddDate(-2, 0, 0), // 2 years ago
			UpdatedAt: now,
			ExpiredAt: func() *time.Time { t := now.AddDate(0, -2, 0); return &t }(), // 2 months ago (expired)
		},
	}

	cm.Accounts = append(cm.Accounts, validAccounts...)
	cm.Accounts = append(cm.Accounts, invalidAccounts...)
}

// generateCategoryUsers creates users with category-specific IDs and FK relationships
func (cm *CategoryMatrix) generateCategoryUsers() {
	now := time.Now().UTC()

	// Basic category users - fundamental CRUD testing
	basicUsers := []models.User{
		{
			ID:             "basic_valid_001",
			Username:       "basic_valid_001", // id == username
			Email:          "basic_valid_001@test.com",
			FirstName:      "Basic",
			LastName:       "ValidUser",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_001",
			Gender:         "male",
			NetWorth:       50000.0,
			IsAccountOwner: true,
			DOB:            time.Date(1985, 6, 15, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "basic_invalid_enum_001",
			Username:       "basic_invalid_enum_001",
			Email:          "basic_invalid_enum_001@test.com",
			FirstName:      "Basic",
			LastName:       "InvalidEnum",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_001",
			Gender:         "invalid_gender", // Invalid enum for validation testing
			NetWorth:       50000.0,
			IsAccountOwner: true,
			DOB:            time.Date(1978, 11, 8, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "basic_invalid_currency_001",
			Username:       "basic_invalid_currency_001",
			Email:          "basic_invalid_currency_001@test.com",
			FirstName:      "Basic",
			LastName:       "InvalidCurrency",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_001",
			Gender:         "female",
			NetWorth:       -5000.0, // Invalid currency (negative)
			IsAccountOwner: true,
			DOB:            time.Date(2001, 12, 25, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "basic_missing_required_001",
			Username:       "basic_missing_required_001",
			Email:          "basic_missing_required_001@test.com",
			FirstName:      "Basic",
			LastName:       "MissingRequired",
			// Password missing - required field
			// AccountID missing - required field
			Gender:         "other",
			NetWorth:       30000.0,
			IsAccountOwner: false,
			DOB:            time.Date(1992, 3, 14, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
	}

	// View category users - FK relationship testing for view parameters
	viewUsers := []models.User{
		{
			ID:             "view_valid_fk_001",
			Username:       "view_valid_fk_001",
			Email:          "view_valid_fk_001@test.com",
			FirstName:      "View",
			LastName:       "ValidFK",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_001", // Valid FK - should populate view data
			Gender:         "male",
			NetWorth:       75000.0,
			IsAccountOwner: true,
			DOB:            time.Date(1990, 3, 20, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "view_valid_fk_002",
			Username:       "view_valid_fk_002",
			Email:          "view_valid_fk_002@test.com",
			FirstName:      "View",
			LastName:       "ValidFK2",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_001", // Valid FK - same account as other valid tests
			Gender:         "female",
			NetWorth:       60000.0,
			IsAccountOwner: false,
			DOB:            time.Date(1992, 7, 14, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "view_invalid_fk_001",
			Username:       "view_invalid_fk_001",
			Email:          "view_invalid_fk_001@test.com",
			FirstName:      "View",
			LastName:       "InvalidFK1",
			Password:       "ValidPass123!",
			AccountID:      "nonexistent_account_123", // Invalid FK - should show exists:false
			Gender:         "male",
			NetWorth:       55000.0,
			IsAccountOwner: true,
			DOB:            time.Date(1991, 8, 10, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "view_invalid_fk_002",
			Username:       "view_invalid_fk_002",
			Email:          "view_invalid_fk_002@test.com",
			FirstName:      "View",
			LastName:       "InvalidFK2",
			Password:       "ValidPass123!",
			AccountID:      "nonexistent_account_456", // Invalid FK - should show exists:false
			Gender:         "female",
			NetWorth:       48000.0,
			IsAccountOwner: false,
			DOB:            time.Date(1993, 4, 18, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "view_expired_fk_001",
			Username:       "view_expired_fk_001",
			Email:          "view_expired_fk_001@test.com",
			FirstName:      "View",
			LastName:       "ExpiredFK",
			Password:       "ValidPass123!",
			AccountID:      "expired_invalid_001", // FK to expired account
			Gender:         "other",
			NetWorth:       45000.0,
			IsAccountOwner: false,
			DOB:            time.Date(1988, 12, 5, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "view_missing_fk_001",
			Username:       "view_missing_fk_001",
			Email:          "view_missing_fk_001@test.com",
			FirstName:      "View",
			LastName:       "MissingFK",
			Password:       "ValidPass123!",
			AccountID:      "nonexistent_account_999", // FK to non-existent account
			Gender:         "male",
			NetWorth:       30000.0,
			IsAccountOwner: false,
			DOB:            time.Date(1995, 4, 10, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "view_null_fk_001",
			Username:       "view_null_fk_001",
			Email:          "view_null_fk_001@test.com",
			FirstName:      "View",
			LastName:       "NullFK",
			Password:       "ValidPass123!",
			AccountID:      "", // Empty/null FK
			Gender:         "female",
			NetWorth:       40000.0,
			IsAccountOwner: false,
			DOB:            time.Date(1993, 8, 22, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
	}

	// Sort category users - diverse data for sorting tests
	sortUsers := []models.User{
		{
			ID:             "sort_alpha_001",
			Username:       "sort_alpha_001",
			Email:          "sort_alpha_001@test.com",
			FirstName:      "Alpha", // A comes first alphabetically
			LastName:       "FirstUser",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_001",
			Gender:         "male",
			NetWorth:       10000.0, // Lowest net worth
			IsAccountOwner: true,
			DOB:            time.Date(2000, 1, 1, 0, 0, 0, 0, time.UTC), // Latest DOB
			CreatedAt:      now.AddDate(0, 0, -10), // 10 days ago
			UpdatedAt:      now,
		},
		{
			ID:             "sort_zulu_001",
			Username:       "sort_zulu_001",
			Email:          "sort_zulu_001@test.com",
			FirstName:      "Zulu", // Z comes last alphabetically
			LastName:       "LastUser",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_002",
			Gender:         "female",
			NetWorth:       100000.0, // Highest net worth
			IsAccountOwner: false,
			DOB:            time.Date(1970, 12, 31, 0, 0, 0, 0, time.UTC), // Earliest DOB
			CreatedAt:      now.AddDate(0, 0, -1), // 1 day ago
			UpdatedAt:      now,
		},
		{
			ID:             "sort_middle_001",
			Username:       "sort_middle_001",
			Email:          "sort_middle_001@test.com",
			FirstName:      "Middle",
			LastName:       "MiddleUser",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_003",
			Gender:         "other",
			NetWorth:       55000.0, // Middle net worth
			IsAccountOwner: true,
			DOB:            time.Date(1985, 6, 15, 0, 0, 0, 0, time.UTC), // Middle DOB
			CreatedAt:      now.AddDate(0, 0, -5), // 5 days ago
			UpdatedAt:      now,
		},
	}

	// Page category users - many records for pagination testing
	pageUsers := []models.User{}
	for i := 1; i <= 25; i++ { // Generate 25 users for robust pagination testing
		user := models.User{
			ID:             fmt.Sprintf("page_user_%03d", i),
			Username:       fmt.Sprintf("page_user_%03d", i),
			Email:          fmt.Sprintf("page_user_%03d@test.com", i),
			FirstName:      "Page",
			LastName:       fmt.Sprintf("User%03d", i),
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_001", // All use same account for consistency
			Gender:         []string{"male", "female", "other"}[i%3], // Rotate genders
			NetWorth:       float64(25000 + (i * 1000)), // Increasing net worth pattern
			IsAccountOwner: i%2 == 1, // Alternate true/false
			DOB:            time.Date(1980+i%20, time.Month((i%12)+1), (i%28)+1, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now.AddDate(0, 0, -i), // Different creation dates
			UpdatedAt:      now,
		}
		pageUsers = append(pageUsers, user)
	}

	// Case category users - test case sensitivity
	caseUsers := []models.User{
		{
			ID:             "case_lower_001",
			Username:       "case_lower_001",
			Email:          "case_lower_001@test.com",
			FirstName:      "lowercase", // All lowercase
			LastName:       "user",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_001",
			Gender:         "male",
			NetWorth:       40000.0,
			IsAccountOwner: true,
			DOB:            time.Date(1990, 1, 1, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "case_upper_001",
			Username:       "case_upper_001",
			Email:          "case_upper_001@test.com",
			FirstName:      "UPPERCASE", // All uppercase
			LastName:       "USER",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_002",
			Gender:         "female",
			NetWorth:       45000.0,
			IsAccountOwner: false,
			DOB:            time.Date(1991, 2, 2, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
		{
			ID:             "case_mixed_001",
			Username:       "case_mixed_001",
			Email:          "case_mixed_001@test.com",
			FirstName:      "MiXeD", // Mixed case
			LastName:       "CaSe",
			Password:       "ValidPass123!",
			AccountID:      "primary_valid_003",
			Gender:         "other",
			NetWorth:       50000.0,
			IsAccountOwner: true,
			DOB:            time.Date(1992, 3, 3, 0, 0, 0, 0, time.UTC),
			CreatedAt:      now,
			UpdatedAt:      now,
		},
	}

	// Combine all users
	cm.Users = append(cm.Users, basicUsers...)
	cm.Users = append(cm.Users, viewUsers...)
	cm.Users = append(cm.Users, sortUsers...)
	cm.Users = append(cm.Users, pageUsers...)
	cm.Users = append(cm.Users, caseUsers...)
}