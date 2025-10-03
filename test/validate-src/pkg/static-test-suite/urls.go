package statictestsuite

import (
	"strings"
	"validate/pkg/types"
)


// determineExpectedStatus determines the expected HTTP status code based on URL pattern and method
func determineExpectedStatus(method, url string) int {
	// Remove query parameters for pattern matching
	baseURL := strings.Split(url, "?")[0]

	switch method {
	case "GET":
		// 404 patterns - only for truly invalid endpoints
		if strings.Contains(baseURL, "InvalidEntity") ||
		   baseURL == "" ||
		   baseURL == "/" ||
		   baseURL == "/api/" {
			return 404
		}

		// Non-existent entities and invalid data return 200 (valid endpoint, no data)
		if strings.Contains(baseURL, "nonexistent") ||
		   strings.Contains(baseURL, "invalid_") {
			return 200
		}

		// 400 patterns for edge cases with bad parameters
		if strings.Contains(url, "sort=invalidField") ||
		   strings.Contains(url, "filter=invalidField") ||
		   strings.Contains(url, "view=invalidEntity") ||
		   strings.Contains(url, "page=0") ||
		   strings.Contains(url, "page=-1") ||
		   strings.Contains(url, "pageSize=0") ||
		   strings.Contains(url, "pageSize=-5") ||
		   strings.Contains(url, "sort=firstName:invalid") ||
		   strings.Contains(url, "filter=netWorth:invalid") ||
		   strings.Contains(url, "view=account()") ||
		   strings.Contains(url, "view=account(invalidField)") {
			return 400
		}

		return 200

	case "POST":
		// Entity endpoints like /api/User, /api/Account should return 201
		if strings.HasSuffix(baseURL, "/api/User") ||
		   strings.HasSuffix(baseURL, "/api/Account") {
			return 201
		}

		// Admin endpoints return 200
		if strings.Contains(baseURL, "/api/db/") ||
		   strings.Contains(baseURL, "/api/test/") {
			return 200
		}

		return 201

	case "PUT":
		// Non-existent entities return 200 (valid endpoint, no data affected)
		if strings.Contains(baseURL, "nonexistent") {
			return 200
		}
		return 200

	case "DELETE":
		// Non-existent entities return 200 (valid endpoint, no data affected)
		if strings.Contains(baseURL, "nonexistent") {
			return 200
		}
		return 200

	default:
		return 200
	}
}

// GetAllTestCases returns all test cases from curl.sh converted to unified TestCase structure
func GetAllTestCases() []types.TestCase {
	testCases := []types.TestCase{
		{Method: "GET", URL: "/api/User/basic_valid_001", TestClass: "basic", Description: "Get valid user"},
		{Method: "GET", URL: "/api/User/basic_invalid_enum_001", TestClass: "basic", Description: "Get user with bad enum"},
		{Method: "GET", URL: "/api/User/basic_invalid_currency_001", TestClass: "basic", Description: "Get user with bad currency"},
		{Method: "GET", URL: "/api/User/basic_missing_required_001", TestClass: "basic", Description: "Get user with missing required fields"},
		{Method: "GET", URL: "/api/User/nonexistent_user_123456", TestClass: "basic", Description: "Get non-existent user"},
		{Method: "GET", URL: "/api/User", TestClass: "basic", Description: "Get user list"},
		{Method: "GET", URL: "/api/user", TestClass: "basic", Description: "Get user list (lowercase entity)"},
		{Method: "GET", URL: "/api/User?pageSize=3", TestClass: "basic", Description: "Get user list with page size"},
		{Method: "GET", URL: "/api/User/view_valid_fk_001?view=account(id)", TestClass: "view", Description: "Get valid user with account ID view"},
		{Method: "GET", URL: "/api/User/view_valid_fk_001?view=account(id,name,createdAt)", TestClass: "view", Description: "Get valid user with full account view"},
		{Method: "GET", URL: "/api/User/view_valid_fk_002?view=account(id,name)", TestClass: "view", Description: "Get valid user with different account view"},
		{Method: "GET", URL: "/api/User/view_invalid_fk_001?view=account(id)", TestClass: "view", Description: "Get user with expired account FK"},
		{Method: "GET", URL: "/api/User/view_missing_fk_001?view=account(id)", TestClass: "view", Description: "Get user with missing account FK"},
		{Method: "GET", URL: "/api/User/view_valid_fk_001?view=account(nonexistent_field)", TestClass: "view", Description: "Get valid user with invalid view field"},
		{Method: "GET", URL: "/api/User/view_valid_fk_001?view=badentity(id)", TestClass: "view", Description: "Get valid user with bad view entity"},
		{Method: "GET", URL: "/api/User?view=account(id)", TestClass: "view", Description: "Get user list with account ID view"},
		{Method: "GET", URL: "/api/User?view=account(id,name,createdAt)", TestClass: "view", Description: "Get user list with full account view"},
		{Method: "GET", URL: "/api/User?pageSize=3&view=account(id)", TestClass: "view", Description: "Get user list with pagination and view"},
		{Method: "GET", URL: "/api/User?pageSize=1&view=account(id,name,createdAt,balance)", TestClass: "view", Description: "Get user list with max view fields"},
		{Method: "GET", URL: "/api/User", TestClass: "page", Description: "Get user list with default pagination"},
		{Method: "GET", URL: "/api/User?pageSize=5", TestClass: "page", Description: "Get user list with page size 5"},
		{Method: "GET", URL: "/api/User?page=1&pageSize=5", TestClass: "page", Description: "Get user list page 1 with size 5"},
		{Method: "GET", URL: "/api/User?page=2&pageSize=5", TestClass: "page", Description: "Get user list page 2 with size 5"},
		{Method: "GET", URL: "/api/User?page=3&pageSize=5", TestClass: "page", Description: "Get user list page 3 with size 5"},
		{Method: "GET", URL: "/api/User?page=1&pageSize=1", TestClass: "page", Description: "Get user list page 1 with size 1"},
		{Method: "GET", URL: "/api/User?page=2&pageSize=1", TestClass: "page", Description: "Get user list page 2 with size 1"},
		{Method: "GET", URL: "/api/User?page=10&pageSize=5", TestClass: "page", Description: "Get user list page 10 (beyond data)"},
		{Method: "GET", URL: "/api/User?pageSize=100", TestClass: "page", Description: "Get user list with large page size"},
		{Method: "GET", URL: "/api/User?sort=firstName", TestClass: "sort", Description: "Sort by firstName ascending"},
		{Method: "GET", URL: "/api/User?sort=firstName:desc", TestClass: "sort", Description: "Sort by firstName descending"},
		{Method: "GET", URL: "/api/User?sort=lastName", TestClass: "sort", Description: "Sort by lastName ascending"},
		{Method: "GET", URL: "/api/User?sort=lastName:desc", TestClass: "sort", Description: "Sort by lastName descending"},
		{Method: "GET", URL: "/api/User?sort=netWorth", TestClass: "sort", Description: "Sort by netWorth ascending"},
		{Method: "GET", URL: "/api/User?sort=netWorth:desc", TestClass: "sort", Description: "Sort by netWorth descending"},
		{Method: "GET", URL: "/api/User?sort=createdAt", TestClass: "sort", Description: "Sort by createdAt ascending"},
		{Method: "GET", URL: "/api/User?sort=createdAt:desc", TestClass: "sort", Description: "Sort by createdAt descending"},
		{Method: "GET", URL: "/api/User?sort=firstName,lastName", TestClass: "sort", Description: "Sort by firstName then lastName"},
		{Method: "GET", URL: "/api/User?sort=firstName:desc,lastName", TestClass: "sort", Description: "Sort by firstName desc then lastName asc"},
		{Method: "GET", URL: "/api/User?sort=firstName:desc,lastName:desc", TestClass: "sort", Description: "Sort by firstName desc then lastName desc"},
		{Method: "GET", URL: "/api/User?sort=netWorth:desc,firstName", TestClass: "sort", Description: "Sort by netWorth desc then firstName asc"},
		{Method: "GET", URL: "/api/User?sort=firstName,lastName,netWorth", TestClass: "sort", Description: "Sort by three fields"},
		{Method: "GET", URL: "/api/User?sort=gender,netWorth:desc", TestClass: "sort", Description: "Sort by gender then netWorth desc"},
		{Method: "GET", URL: "/api/User?filter=firstName:Basic", TestClass: "filter", Description: "Filter by firstName contains 'Basic'"},
		{Method: "GET", URL: "/api/User?filter=lastName:User", TestClass: "filter", Description: "Filter by lastName contains 'User'"},
		{Method: "GET", URL: "/api/User?filter=gender:male", TestClass: "filter", Description: "Filter by gender male"},
		{Method: "GET", URL: "/api/User?filter=gender:female", TestClass: "filter", Description: "Filter by gender female"},
		{Method: "GET", URL: "/api/User?filter=isAccountOwner:true", TestClass: "filter", Description: "Filter by isAccountOwner true"},
		{Method: "GET", URL: "/api/User?filter=isAccountOwner:false", TestClass: "filter", Description: "Filter by isAccountOwner false"},
		{Method: "GET", URL: "/api/User?filter=netWorth:gt:50000", TestClass: "filter", Description: "Filter by netWorth > 50k"},
		{Method: "GET", URL: "/api/User?filter=netWorth:gte:50000", TestClass: "filter", Description: "Filter by netWorth >= 50k"},
		{Method: "GET", URL: "/api/User?filter=netWorth:lt:100000", TestClass: "filter", Description: "Filter by netWorth < 100k"},
		{Method: "GET", URL: "/api/User?filter=netWorth:lte:100000", TestClass: "filter", Description: "Filter by netWorth <= 100k"},
		{Method: "GET", URL: "/api/User?filter=netWorth:eq:75000", TestClass: "filter", Description: "Filter by netWorth = 75k"},
		{Method: "GET", URL: "/api/User?filter=gender:male,isAccountOwner:true", TestClass: "filter", Description: "Filter by gender male and account owner"},
		{Method: "GET", URL: "/api/User?filter=gender:female,netWorth:gte:50000", TestClass: "filter", Description: "Filter by gender female and wealthy"},
		{Method: "GET", URL: "/api/User?filter=firstName:View,gender:male", TestClass: "filter", Description: "Filter by firstName and gender"},
		{Method: "GET", URL: "/api/User?filter=netWorth:gte:25000,netWorth:lte:75000", TestClass: "filter", Description: "Filter by netWorth range"},
		{Method: "GET", URL: "/api/User?pagesize=5", TestClass: "case", Description: "pagesize parameter (lowercase)"},
		{Method: "GET", URL: "/api/User?PAGESIZE=5", TestClass: "case", Description: "PAGESIZE parameter (uppercase)"},
		{Method: "GET", URL: "/api/User?PageSize=5", TestClass: "case", Description: "PageSize parameter (mixed case)"},
		{Method: "GET", URL: "/api/User?page=2&pagesize=3", TestClass: "case", Description: "Mixed case page and pagesize"},
		{Method: "GET", URL: "/api/User?sort=firstname", TestClass: "case", Description: "Sort by firstname (lowercase)"},
		{Method: "GET", URL: "/api/User?sort=FIRSTNAME", TestClass: "case", Description: "Sort by FIRSTNAME (uppercase)"},
		{Method: "GET", URL: "/api/User?sort=FirstName", TestClass: "case", Description: "Sort by FirstName (mixed case)"},
		{Method: "GET", URL: "/api/User?sort=lastname:desc", TestClass: "case", Description: "Sort by lastname desc (lowercase)"},
		{Method: "GET", URL: "/api/User?filter=firstname:Basic", TestClass: "case", Description: "Filter by firstname (lowercase)"},
		{Method: "GET", URL: "/api/User?filter=FIRSTNAME:Basic", TestClass: "case", Description: "Filter by FIRSTNAME (uppercase)"},
		{Method: "GET", URL: "/api/User?filter=FirstName:Basic", TestClass: "case", Description: "Filter by FirstName (mixed case)"},
		{Method: "GET", URL: "/api/User?filter=GENDER:male", TestClass: "case", Description: "Filter by GENDER (uppercase)"},
		{Method: "GET", URL: "/api/User?filter=gender:MALE", TestClass: "case", Description: "Filter by gender with MALE value"},
		{Method: "GET", URL: "/api/User?Page=1&PageSize=5", TestClass: "case", Description: "Mixed case Page and PageSize"},
		{Method: "GET", URL: "/api/User?view=account(id)&sort=firstName", TestClass: "combo", Description: "View with sort"},
		{Method: "GET", URL: "/api/User?view=account(id,name)&sort=firstName:desc", TestClass: "combo", Description: "Full account view with sort desc"},
		{Method: "GET", URL: "/api/User?view=account(id)&filter=gender:male", TestClass: "combo", Description: "View with filter"},
		{Method: "GET", URL: "/api/User?view=account(id,name,balance)&filter=gender:female", TestClass: "combo", Description: "Full account view with filter"},
		{Method: "GET", URL: "/api/User?sort=firstName&filter=gender:female", TestClass: "combo", Description: "Sort with filter"},
		{Method: "GET", URL: "/api/User?sort=netWorth:desc&filter=isAccountOwner:true", TestClass: "combo", Description: "Sort by wealth with account owner filter"},
		{Method: "GET", URL: "/api/User?view=account(id)&sort=firstName&filter=gender:male", TestClass: "combo", Description: "View + sort + filter"},
		{Method: "GET", URL: "/api/User?view=account(id,name,createdAt)&sort=firstName&filter=gender:male", TestClass: "combo", Description: "Full view + sort + filter"},
		{Method: "GET", URL: "/api/User?view=account(id)&sort=firstName&filter=gender:male&pageSize=3", TestClass: "combo", Description: "All parameters: view + sort + filter + pagination"},
		{Method: "GET", URL: "/api/User?view=account(id,name,balance)&sort=netWorth:desc&filter=isAccountOwner:true&pageSize=2", TestClass: "combo", Description: "All parameters with wealth focus"},
		{Method: "GET", URL: "/api/User?view=account(id)&sort=lastName,firstName&filter=gender:female,netWorth:gte:50000&page=2&pageSize=3", TestClass: "combo", Description: "Complex multi-field combo"},
		// CRUD Success Cases - User
		{Method: "POST", URL: "/api/User", TestClass: "crud", Description: "Create user with valid data",
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "test.user@example.com",
				"username": "test_user_crud", "gender": "male", "isAccountOwner": true,
				"netWorth": 50000, "dob": "1990-01-01", "password": "testpass123", "accountId": "valid_account_001"},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "firstName", "lastName", "email", "username", "createdAt"},
			}},

		{Method: "POST", URL: "/api/User?novalidate", TestClass: "crud", Description: "Create user without validation",
			RequestBody: map[string]interface{}{
				"firstName": "NoValidate", "lastName": "User", "email": "novalidate@example.com",
				"username": "novalidate_user", "gender": "invalid_gender", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "firstName", "lastName", "email", "username"},
			}},

		{Method: "PUT", URL: "/api/User/basic_valid_001", TestClass: "crud", Description: "Update user with valid data",
			RequestBody: map[string]interface{}{
				"firstName": "Updated", "lastName": "UserName", "netWorth": 75000},
			ExpectedData: &types.CRUDExpectation{
				ExpectedFields: map[string]interface{}{"firstName": "Updated", "lastName": "UserName", "netWorth": float64(75000)},
				ShouldContainFields: []string{"id", "updatedAt"},
			}},

		{Method: "PUT", URL: "/api/User/basic_valid_001?novalidate", TestClass: "crud", Description: "Update user without validation",
			RequestBody: map[string]interface{}{
				"firstName": "NoValidateUpdate", "gender": "invalid_gender"},
			ExpectedData: &types.CRUDExpectation{
				ExpectedFields: map[string]interface{}{"firstName": "NoValidateUpdate"},
				ShouldContainFields: []string{"id", "updatedAt"},
			}},

		{Method: "DELETE", URL: "/api/User/crud_delete_test_001", TestClass: "crud", Description: "Delete existing user"},

		// CRUD Success Cases - Account
		{Method: "POST", URL: "/api/Account", TestClass: "crud", Description: "Create account with valid data",
			RequestBody: map[string]interface{}{
				"name": "Test Account", "balance": 1000.50, "currency": "USD", "isActive": true},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "name", "balance", "currency", "isActive", "createdAt"},
				ExpectedFields: map[string]interface{}{"name": "Test Account", "balance": 1000.50, "currency": "USD"},
			}},

		{Method: "POST", URL: "/api/Account?novalidate", TestClass: "crud", Description: "Create account without validation",
			RequestBody: map[string]interface{}{
				"name": "NoValidate Account", "balance": -500, "currency": "INVALID"},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "name", "createdAt"},
			}},

		{Method: "PUT", URL: "/api/Account/valid_account_001", TestClass: "crud", Description: "Update account with valid data",
			RequestBody: map[string]interface{}{
				"name": "Updated Account", "balance": 2000.75},
			ExpectedData: &types.CRUDExpectation{
				ExpectedFields: map[string]interface{}{"name": "Updated Account", "balance": 2000.75},
				ShouldContainFields: []string{"id", "updatedAt"},
			}},

		{Method: "PUT", URL: "/api/Account/valid_account_001?novalidate", TestClass: "crud", Description: "Update account without validation",
			RequestBody: map[string]interface{}{
				"name": "NoValidate Update", "balance": -1000},
			ExpectedData: &types.CRUDExpectation{
				ExpectedFields: map[string]interface{}{"name": "NoValidate Update"},
				ShouldContainFields: []string{"id", "updatedAt"},
			}},

		{Method: "DELETE", URL: "/api/Account/crud_delete_account_001", TestClass: "crud", Description: "Delete existing account"},
		// CRUD Failure Cases - User
		{Method: "POST", URL: "/api/User", TestClass: "failure", Description: "Create user with missing required field",
			RequestBody: map[string]interface{}{
				"firstName": "Incomplete", "lastName": "User"}, // Missing email, username
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "validation",
			}},

		{Method: "POST", URL: "/api/User", TestClass: "failure", Description: "Create user with invalid enum",
			RequestBody: map[string]interface{}{
				"firstName": "Invalid", "lastName": "Enum", "email": "invalid.enum@example.com",
				"username": "invalid_enum", "gender": "invalid_gender"},
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "validation",
			}},

		{Method: "POST", URL: "/api/User", TestClass: "failure", Description: "Create user with duplicate username",
			RequestBody: map[string]interface{}{
				"firstName": "Duplicate", "lastName": "User", "email": "duplicate@example.com",
				"username": "basic_valid_001", "password": "testpass123", "accountId": "valid_account_001",
				"gender": "male", "isAccountOwner": false}, // Existing username
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "constraint",
			}},

		{Method: "POST", URL: "/api/User", TestClass: "failure", Description: "Create user - first creation (should succeed)",
			RequestBody: map[string]interface{}{
				"firstName": "UniqueTest", "lastName": "FirstAttempt", "email": "uniquetest@example.com",
				"username": "unique_constraint_test", "password": "testpass123", "accountId": "valid_account_001",
				"gender": "male", "isAccountOwner": false, "netWorth": 25000},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "firstName", "lastName", "email", "username", "createdAt"},
				ExpectedFields: map[string]interface{}{"username": "unique_constraint_test", "email": "uniquetest@example.com"},
			}},

		{Method: "POST", URL: "/api/User", TestClass: "failure", Description: "Create user - duplicate attempt (should fail)",
			RequestBody: map[string]interface{}{
				"firstName": "UniqueTest", "lastName": "SecondAttempt", "email": "uniquetest@example.com",
				"username": "unique_constraint_test", "password": "testpass123", "accountId": "valid_account_001",
				"gender": "female", "isAccountOwner": true, "netWorth": 50000},
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "constraint",
			}},

		{Method: "PUT", URL: "/api/User/nonexistent_user_123456", TestClass: "failure", Description: "Update non-existent user",
			RequestBody: map[string]interface{}{
				"firstName": "NonExistent", "lastName": "Update"},
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "not_found",
			}},

		{Method: "PUT", URL: "/api/User/basic_valid_001", TestClass: "failure", Description: "Update user with invalid data",
			RequestBody: map[string]interface{}{
				"gender": "invalid_gender", "netWorth": "not_a_number"},
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "validation",
			}},

		{Method: "DELETE", URL: "/api/User/nonexistent_user_123456", TestClass: "failure", Description: "Delete non-existent user",
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "not_found",
			}},

		// CRUD Failure Cases - Account
		{Method: "POST", URL: "/api/Account", TestClass: "failure", Description: "Create account with missing required field",
			RequestBody: map[string]interface{}{
				"balance": 1000}, // Missing name
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "validation",
			}},

		{Method: "POST", URL: "/api/Account", TestClass: "failure", Description: "Create account with invalid currency",
			RequestBody: map[string]interface{}{
				"name": "Invalid Currency", "balance": 1000, "currency": "INVALID"},
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "validation",
			}},

		{Method: "POST", URL: "/api/Account", TestClass: "failure", Description: "Create account - first creation (should succeed)",
			RequestBody: map[string]interface{}{
				"name": "Unique Account Test", "balance": 5000.0, "currency": "USD", "isActive": true},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "name", "balance", "currency", "isActive", "createdAt"},
				ExpectedFields: map[string]interface{}{"name": "Unique Account Test", "balance": 5000.0, "currency": "USD"},
			}},

		{Method: "POST", URL: "/api/Account", TestClass: "failure", Description: "Create account - duplicate attempt (should fail)",
			RequestBody: map[string]interface{}{
				"name": "Unique Account Test", "balance": 10000.0, "currency": "EUR", "isActive": false}, // Same name
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "constraint",
			}},

		{Method: "PUT", URL: "/api/Account/nonexistent_account_123456", TestClass: "failure", Description: "Update non-existent account",
			RequestBody: map[string]interface{}{
				"name": "NonExistent Update"},
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "not_found",
			}},

		{Method: "DELETE", URL: "/api/Account/nonexistent_account_123456", TestClass: "failure", Description: "Delete non-existent account",
			ExpectedData: &types.CRUDExpectation{
				ExpectedErrorType: "not_found",
			}},
		{Method: "GET", URL: "/api/db/report", TestClass: "admin", Description: "Get database status report"},
		{Method: "POST", URL: "/api/db/init", TestClass: "admin", Description: "Initialize database"},
		{Method: "POST", URL: "/api/db/wipe", TestClass: "admin", Description: "Wipe database"},
		{Method: "GET", URL: "/api/db/health", TestClass: "admin", Description: "Get database health"},
		{Method: "GET", URL: "/api/test/populate", TestClass: "admin", Description: "Populate test data"},
		{Method: "GET", URL: "/api/test/validate", TestClass: "admin", Description: "Validate all test data"},
		{Method: "GET", URL: "/api/test/cleanup", TestClass: "admin", Description: "Cleanup test data"},
		{Method: "GET", URL: "/api/User?sort=invalidField", TestClass: "edge", Description: "Sort by invalid field"},
		{Method: "GET", URL: "/api/User?filter=invalidField:value", TestClass: "edge", Description: "Filter by invalid field"},
		{Method: "GET", URL: "/api/User?view=invalidEntity(id)", TestClass: "edge", Description: "View invalid entity"},
		{Method: "GET", URL: "/api/User?page=0", TestClass: "edge", Description: "Page 0 (invalid)"},
		{Method: "GET", URL: "/api/User?page=-1", TestClass: "edge", Description: "Negative page number"},
		{Method: "GET", URL: "/api/User?pageSize=0", TestClass: "edge", Description: "Page size 0"},
		{Method: "GET", URL: "/api/User?pageSize=-5", TestClass: "edge", Description: "Negative page size"},
		{Method: "GET", URL: "/api/User?pageSize=1000", TestClass: "edge", Description: "Very large page size"},
		{Method: "GET", URL: "/api/User?sort=", TestClass: "edge", Description: "Empty sort parameter"},
		{Method: "GET", URL: "/api/User?filter=", TestClass: "edge", Description: "Empty filter parameter"},
		{Method: "GET", URL: "/api/User?view=", TestClass: "edge", Description: "Empty view parameter"},
		{Method: "GET", URL: "/api/User?sort=firstName:invalid", TestClass: "edge", Description: "Invalid sort direction"},
		{Method: "GET", URL: "/api/User?filter=netWorth:invalid:50000", TestClass: "edge", Description: "Invalid filter operator"},
		{Method: "GET", URL: "/api/User?view=account()", TestClass: "edge", Description: "Empty view fields"},
		{Method: "GET", URL: "/api/User?view=account(invalidField)", TestClass: "edge", Description: "Invalid view field"},
		{Method: "GET", URL: "/api/User?unknown=parameter", TestClass: "edge", Description: "Unknown query parameter"},
		{Method: "GET", URL: "/api/User?sort=firstName&sort=lastName", TestClass: "edge", Description: "Duplicate sort parameters"},
		{Method: "GET", URL: "/api/User?filter=gender:male&filter=gender:female", TestClass: "edge", Description: "Duplicate filter parameters"},
		{Method: "GET", URL: "/api/User?view=account(id)&view=profile(name)", TestClass: "edge", Description: "Duplicate view parameters"},
		{Method: "GET", URL: "/api/InvalidEntity", TestClass: "edge", Description: "Invalid entity endpoint"},
		{Method: "GET", URL: "/api/User/", TestClass: "edge", Description: "Trailing slash on entity"},
		{Method: "GET", URL: "/api/User//", TestClass: "edge", Description: "Double slash in URL"},
		{Method: "GET", URL: "/api/", TestClass: "edge", Description: "API root endpoint"},
		{Method: "GET", URL: "/", TestClass: "edge", Description: "Root endpoint"},
		{Method: "GET", URL: "/api/User?%20invalid=space", TestClass: "edge", Description: "URL with special characters"},
		{Method: "GET", URL: "/api/User?sort=firstName%2Cdesc", TestClass: "edge", Description: "URL encoded sort parameter"},
		{Method: "GET", URL: "/api/User?filter=firstName%3ABasic", TestClass: "edge", Description: "URL encoded filter parameter"},
		{Method: "POST", URL: "/api/User?pageSize=5", TestClass: "edge", Description: "POST with query parameters"},
		{Method: "PUT", URL: "/api/User?sort=firstName", TestClass: "edge", Description: "PUT with query parameters"},
		{Method: "DELETE", URL: "/api/User?filter=gender:male", TestClass: "edge", Description: "DELETE with query parameters"},
		{Method: "GET", URL: "/api/User?sort=firstName,", TestClass: "edge", Description: "Sort with trailing comma"},
		{Method: "GET", URL: "/api/User?filter=gender:male,", TestClass: "edge", Description: "Filter with trailing comma"},
		{Method: "GET", URL: "/api/User?view=account(id,)", TestClass: "edge", Description: "View with trailing comma"},
		{Method: "GET", URL: "/api/User?sort=,firstName", TestClass: "edge", Description: "Sort with leading comma"},
		{Method: "GET", URL: "/api/User?filter=,gender:male", TestClass: "edge", Description: "Filter with leading comma"},
		{Method: "GET", URL: "/api/User?view=account(,id)", TestClass: "edge", Description: "View with leading comma"},
		{Method: "GET", URL: "/api/User?sort=firstName,,lastName", TestClass: "edge", Description: "Sort with double comma"},
		{Method: "GET", URL: "/api/User?filter=gender:male,,isAccountOwner:true", TestClass: "edge", Description: "Filter with double comma"},
		{Method: "GET", URL: "/api/User?view=account(id,,name)", TestClass: "edge", Description: "View with double comma"},

		// Missing database health endpoints
		{Method: "GET", URL: "/api/db/health", TestClass: "admin", Description: "Database health check"},
		{Method: "GET", URL: "/api/db/report", TestClass: "admin", Description: "Database status report"},

		// Missing test utility endpoints
		{Method: "GET", URL: "/api/test/cleanup", TestClass: "admin", Description: "Cleanup test data"},
		{Method: "GET", URL: "/api/test/populate", TestClass: "admin", Description: "Populate test data"},
		{Method: "GET", URL: "/api/test/validate", TestClass: "admin", Description: "Validate test data"},

		// Missing invalid entity endpoint
		{Method: "GET", URL: "/api/InvalidEntity", TestClass: "invalid", Description: "Invalid entity endpoint"},

		// Missing root endpoint
		{Method: "GET", URL: "/", TestClass: "basic", Description: "Root endpoint"},
		{Method: "GET", URL: "/api/", TestClass: "basic", Description: "API root endpoint"},

		// Missing date filtering tests
		{Method: "GET", URL: "/api/User?filter=createdat:gte:2023-01-01", TestClass: "filter", Description: "Filter by creation date >= 2023"},
		{Method: "GET", URL: "/api/User?filter=createdat:lt:2024-01-01", TestClass: "filter", Description: "Filter by creation date < 2024"},
		{Method: "GET", URL: "/api/User?filter=dob:1985-06-15", TestClass: "filter", Description: "Filter by exact date of birth"},
		{Method: "GET", URL: "/api/User?filter=dob:1992-03-20", TestClass: "filter", Description: "Filter by exact date of birth 2"},
		{Method: "GET", URL: "/api/User?filter=dob:2050-01-01", TestClass: "filter", Description: "Filter by future date of birth"},
		{Method: "GET", URL: "/api/User?filter=dob:gt:1950-01-01", TestClass: "filter", Description: "Filter by DOB > 1950"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1950-01-01", TestClass: "filter", Description: "Filter by DOB >= 1950"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1950-01-01,dob:lt:2000-01-01,gender:male", TestClass: "filter", Description: "Complex date and gender filter"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1950-01-01,dob:lte:2050-12-31", TestClass: "filter", Description: "Date range filter wide"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1985-01-01,dob:lt:1995-12-31", TestClass: "filter", Description: "Date range filter narrow"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1990-01-01", TestClass: "filter", Description: "Filter by DOB >= 1990"},
		{Method: "GET", URL: "/api/User?filter=dob:lt:2000-01-01", TestClass: "filter", Description: "Filter by DOB < 2000"},
		{Method: "GET", URL: "/api/User?filter=dob:lt:2050-01-01", TestClass: "filter", Description: "Filter by DOB < 2050"},
		{Method: "GET", URL: "/api/User?filter=dob:lte:2050-12-31", TestClass: "filter", Description: "Filter by DOB <= 2050"},

		// Missing email filtering tests
		{Method: "GET", URL: "/api/User?filter=email:test@example.com", TestClass: "filter", Description: "Filter by email address"},
		{Method: "GET", URL: "/api/User?filter=email:valid_all@test.com", TestClass: "filter", Description: "Filter by specific email"},

		// Missing username filtering tests
		{Method: "GET", URL: "/api/User?filter=username:valid_all_user", TestClass: "filter", Description: "Filter by username"},

		// Missing additional date field filtering
		{Method: "GET", URL: "/api/User?filter=updatedat:gt:2023-06-01", TestClass: "filter", Description: "Filter by updated date > June 2023"},
		{Method: "GET", URL: "/api/User?filter=updatedat:lte:2024-12-31", TestClass: "filter", Description: "Filter by updated date <= 2024"},

		// Missing case sensitivity variations for fields
		{Method: "GET", URL: "/api/User?filter=networth:gt:1000", TestClass: "case", Description: "Filter by networth (lowercase)"},
		{Method: "GET", URL: "/api/User?filter=networth:gte:1000", TestClass: "case", Description: "Filter by networth gte (lowercase)"},
		{Method: "GET", URL: "/api/User?filter=isaccountowner:true", TestClass: "case", Description: "Filter by isaccountowner (lowercase)"},
	}

	// Add ID and ExpectedStatus to each test case
	for i := range testCases {
		testCases[i].ID = i + 1
		testCases[i].ExpectedStatus = determineExpectedStatus(testCases[i].Method, testCases[i].URL)
	}

	return testCases
}

// GetTestCasesByClass returns test cases filtered by test class
func GetTestCasesByClass(testClass string) []types.TestCase {
	var filtered []types.TestCase
	for _, tc := range GetAllTestCases() {
		if tc.TestClass == testClass {
			filtered = append(filtered, tc)
		}
	}
	return filtered
}