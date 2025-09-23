package testcases

// generateTestCases creates comprehensive test case specifications for all categories
func (cm *CategoryMatrix) generateTestCases() {
	// Basic API Tests
	cm.addBasicTests()

	// View Parameter Tests
	cm.addViewTests()

	// Individual User + View Edge Cases
	cm.addIndividualViewTests()

	// View + Parameter Combinations
	cm.addViewComboTests()

	// Pagination Tests
	cm.addPaginationTests()

	// Filtering Tests (Comprehensive)
	cm.addFilteringTests()

	// Sorting Tests (Comprehensive)
	cm.addSortingTests()

	// Case Sensitivity Tests (Comprehensive)
	cm.addCaseTests()

	// Invalid Field Tests
	cm.addInvalidFieldTests()

	// Mixed Case Field Tests
	cm.addMixedCaseFieldTests()
}

// addBasicTests adds fundamental CRUD and validation tests
func (cm *CategoryMatrix) addBasicTests() {
	basicTests := []TestSpec{
		// Individual user retrieval
		{"basic_valid_001", "primary_valid_001", "/api/User/basic_valid_001", "Get valid user", "GET", "basic"},
		{"basic_invalid_enum_001", "primary_valid_001", "/api/User/basic_invalid_enum_001", "Get user with bad enum", "GET", "basic"},
		{"basic_invalid_currency_001", "primary_valid_001", "/api/User/basic_invalid_currency_001", "Get user with bad currency", "GET", "basic"},
		{"basic_missing_required_001", "", "/api/User/basic_missing_required_001", "Get user with missing required fields", "GET", "basic"},

		// Non-existent user
		{"", "", "/api/User/nonexistent_user_123456", "Get non-existent user", "GET", "basic"},

		// User list operations
		{"", "", "/api/User", "Get user list", "GET", "basic"},
		{"", "", "/api/user", "Get user list (lowercase entity)", "GET", "basic"},
		{"", "", "/api/User?pageSize=3", "Get user list with page size", "GET", "basic"},
	}

	cm.TestCases = append(cm.TestCases, basicTests...)
}

// addViewTests adds view parameter FK relationship tests
func (cm *CategoryMatrix) addViewTests() {
	viewTests := []TestSpec{
		// Valid FK view tests
		{"view_valid_fk_001", "primary_valid_001", "/api/User/view_valid_fk_001?view=account(id)", "Get valid user with account ID view", "GET", "view"},
		{"view_valid_fk_001", "primary_valid_001", "/api/User/view_valid_fk_001?view=account(id,createdAt)", "Get valid user with account view (id,createdAt)", "GET", "view"},
		{"view_valid_fk_002", "primary_valid_001", "/api/User/view_valid_fk_002?view=account(id)", "Get valid user with account ID view", "GET", "view"},

		// Invalid FK view tests (using same view parameters as above but with invalid accountIds)
		{"view_invalid_fk_001", "nonexistent_account_123", "/api/User/view_invalid_fk_001?view=account(id,createdAt)", "Get user with invalid accountId (id,createdAt view)", "GET", "view"},
		{"view_invalid_fk_002", "nonexistent_account_456", "/api/User/view_invalid_fk_002?view=account(id)", "Get user with invalid accountId (id view)", "GET", "view"},

		// Invalid FK view tests
		{"view_expired_fk_001", "expired_invalid_001", "/api/User/view_expired_fk_001?view=account(id)", "Get user with expired account FK", "GET", "view"},
		{"view_missing_fk_001", "nonexistent_account_999", "/api/User/view_missing_fk_001?view=account(id)", "Get user with missing account FK", "GET", "view"},
		{"view_null_fk_001", "", "/api/User/view_null_fk_001?view=account(id)", "Get user with null account FK", "GET", "view"},

		// Invalid view parameters
		{"view_valid_fk_001", "primary_valid_001", "/api/User/view_valid_fk_001?view=account(nonexistent_field)", "Get valid user with invalid view field", "GET", "view"},
		{"view_valid_fk_001", "primary_valid_001", "/api/User/view_valid_fk_001?view=badentity(id)", "Get valid user with bad view entity", "GET", "view"},

		// List views with FKs
		{"", "", "/api/User?view=account(id)", "Get user list with account ID view", "GET", "view"},
		{"", "", "/api/User?view=account(id,createdAt)", "Get user list with account view", "GET", "view"},
		{"", "", "/api/User?view=badentity(id)", "Get user list with bad entity view", "GET", "view"},
		{"", "", "/api/User?view=account(id,badfield)", "Get user list with bad account field", "GET", "view"},
		{"", "", "/api/User?pageSize=3&view=account(id)", "Get user list with pagination and view", "GET", "view"},
	}

	cm.TestCases = append(cm.TestCases, viewTests...)
}

// addPaginationTests adds pagination-specific tests
func (cm *CategoryMatrix) addPaginationTests() {
	pageTests := []TestSpec{
		// Basic pagination
		{"", "", "/api/User", "Get user list with default pagination", "GET", "page"},
		{"", "", "/api/User?pageSize=5", "Get user list with page size 5", "GET", "page"},
		{"", "", "/api/User?page=1&pageSize=5", "Get user list page 1 with size 5", "GET", "page"},
		{"", "", "/api/User?page=2&pageSize=5", "Get user list page 2 with size 5", "GET", "page"},
		{"", "", "/api/User?page=3&pageSize=5", "Get user list page 3 with size 5", "GET", "page"},

		// Large page sizes
		{"", "", "/api/User?pageSize=20", "Get user list with large page size", "GET", "page"},
		{"", "", "/api/User?page=1&pageSize=10", "Get user list page 1 with size 10", "GET", "page"},
		{"", "", "/api/User?page=2&pageSize=10", "Get user list page 2 with size 10", "GET", "page"},

		// Edge cases
		{"", "", "/api/User?page=100&pageSize=5", "Get user list beyond available pages", "GET", "page"},
		{"page_user_001", "primary_valid_001", "/api/User/page_user_001?page=2&pageSize=10", "Get individual user with pagination params", "GET", "page"},
	}

	cm.TestCases = append(cm.TestCases, pageTests...)
}

// addSortingTests adds comprehensive sorting operation tests
func (cm *CategoryMatrix) addSortingTests() {
	sortTests := []TestSpec{
		// Single field sorting - all field types
		{"", "", "/api/User?sort=username", "Sort by username ascending", "GET", "sort"},
		{"", "", "/api/User?sort=username:desc", "Sort by username descending", "GET", "sort"},
		{"", "", "/api/User?sort=firstName", "Sort by firstName ascending", "GET", "sort"},
		{"", "", "/api/User?sort=firstName:desc", "Sort by firstName descending", "GET", "sort"},
		{"", "", "/api/User?sort=lastName", "Sort by lastName ascending", "GET", "sort"},
		{"", "", "/api/User?sort=lastName:desc", "Sort by lastName descending", "GET", "sort"},
		{"", "", "/api/User?sort=email", "Sort by email ascending", "GET", "sort"},
		{"", "", "/api/User?sort=email:desc", "Sort by email descending", "GET", "sort"},
		{"", "", "/api/User?sort=netWorth", "Sort by netWorth ascending", "GET", "sort"},
		{"", "", "/api/User?sort=netWorth:desc", "Sort by netWorth descending", "GET", "sort"},
		{"", "", "/api/User?sort=dob", "Sort by date of birth ascending", "GET", "sort"},
		{"", "", "/api/User?sort=dob:desc", "Sort by date of birth descending", "GET", "sort"},
		{"", "", "/api/User?sort=createdAt", "Sort by createdAt ascending", "GET", "sort"},
		{"", "", "/api/User?sort=createdAt:desc", "Sort by createdAt descending", "GET", "sort"},
		{"", "", "/api/User?sort=isAccountOwner", "Sort by isAccountOwner ascending", "GET", "sort"},
		{"", "", "/api/User?sort=isAccountOwner:desc", "Sort by isAccountOwner descending", "GET", "sort"},
		{"", "", "/api/User?sort=gender", "Sort by gender ascending", "GET", "sort"},
		{"", "", "/api/User?sort=gender:desc", "Sort by gender descending", "GET", "sort"},

		// Multi-field sorting combinations
		{"", "", "/api/User?sort=firstName,lastName", "Sort by firstName then lastName (both asc)", "GET", "sort"},
		{"", "", "/api/User?sort=firstName:desc,lastName", "Sort by firstName desc then lastName asc", "GET", "sort"},
		{"", "", "/api/User?sort=firstName,lastName:desc", "Sort by firstName asc then lastName desc", "GET", "sort"},
		{"", "", "/api/User?sort=firstName:desc,lastName:desc", "Sort by firstName desc then lastName desc", "GET", "sort"},
		{"", "", "/api/User?sort=dob,netWorth", "Sort by date then currency (both asc)", "GET", "sort"},
		{"", "", "/api/User?sort=dob:desc,netWorth", "Sort by date desc then currency asc", "GET", "sort"},
		{"", "", "/api/User?sort=gender,firstName,netWorth", "Sort by enum, string, then currency", "GET", "sort"},
		{"", "", "/api/User?sort=isAccountOwner,dob:desc,firstName", "Sort by boolean, date desc, then string", "GET", "sort"},
		{"", "", "/api/User?sort=dob,updatedAt", "Sort by dob + auto date fields", "GET", "sort"},

		// Edge cases
		{"", "", "/api/User?sort=firstName,firstName", "Sort by same field twice (edge case)", "GET", "sort"},
		{"sort_alpha_001", "primary_valid_001", "/api/User/sort_alpha_001?sort=username", "Get individual user with sort parameter", "GET", "sort"},
	}

	cm.TestCases = append(cm.TestCases, sortTests...)
}

// addFilteringTests adds comprehensive filtering operation tests
func (cm *CategoryMatrix) addFilteringTests() {
	filterTests := []TestSpec{
		// String field filtering (exact and contains)
		{"", "", "/api/User?filter=username:valid_all_user", "Filter by username (contains match)", "GET", "filter"},
		{"", "", "/api/User?filter=firstName:Valid", "Filter by firstName (contains 'Valid')", "GET", "filter"},
		{"", "", "/api/User?filter=lastName:User", "Filter by lastName (contains 'User')", "GET", "filter"},
		{"", "", "/api/User?filter=email:valid_all@test.com", "Filter by email (contains match)", "GET", "filter"},

		// Boolean filtering
		{"", "", "/api/User?filter=isAccountOwner:true", "Filter by isAccountOwner true", "GET", "filter"},
		{"", "", "/api/User?filter=isAccountOwner:false", "Filter by isAccountOwner false", "GET", "filter"},

		// Enum filtering
		{"", "", "/api/User?filter=gender:male", "Filter by gender male", "GET", "filter"},
		{"", "", "/api/User?filter=gender:female", "Filter by gender female", "GET", "filter"},
		{"", "", "/api/User?filter=gender:invalid_gender", "Filter by invalid gender (edge case)", "GET", "filter"},

		// Currency exact and range filtering
		{"", "", "/api/User?filter=netWorth:50000.0", "Filter by netWorth exact match", "GET", "filter"},
		{"", "", "/api/User?filter=netWorth:75000.0", "Filter by different netWorth value", "GET", "filter"},
		{"", "", "/api/User?filter=netWorth:-5000.0", "Filter by negative netWorth", "GET", "filter"},
		{"", "", "/api/User?filter=netWorth:gte:50000", "Filter by netWorth greater than or equal 50k", "GET", "filter"},
		{"", "", "/api/User?filter=netWorth:lt:0", "Filter by negative netWorth using comparison", "GET", "filter"},

		// Date exact and range filtering
		{"", "", "/api/User?filter=dob:1985-06-15", "Filter by exact date of birth", "GET", "filter"},
		{"", "", "/api/User?filter=dob:1992-03-20", "Filter by non-existant dob", "GET", "filter"},
		{"", "", "/api/User?filter=dob:gte:1950-01-01", "Filter by dob greater than or equal 1950 (broader range)", "GET", "filter"},
		{"", "", "/api/User?filter=dob:lte:2050-12-31", "Filter by dob less than or equal 2050 (broader range)", "GET", "filter"},
		{"", "", "/api/User?filter=dob:gt:1950-01-01", "Filter by dob greater than 1950 (broader range)", "GET", "filter"},
		{"", "", "/api/User?filter=dob:lt:2050-01-01", "Filter by dob less than 2050 (broader range)", "GET", "filter"},

		// Range combinations
		{"", "", "/api/User?filter=dob:gte:1950-01-01,dob:lte:2050-12-31", "Filter by dob range 1950-2050 (broader)", "GET", "filter"},
		{"", "", "/api/User?filter=netWorth:gte:-10000,netWorth:lte:100000", "Filter by netWorth range (including negatives)", "GET", "filter"},

		// Multi-field combinations
		{"", "", "/api/User?filter=gender:male,isAccountOwner:true", "Filter by gender and account owner", "GET", "filter"},
		{"", "", "/api/User?filter=gender:female,netWorth:75000.0", "Filter by gender and netWorth", "GET", "filter"},
		{"", "", "/api/User?filter=isAccountOwner:true,dob:gte:1960-01-01", "Filter by boolean and date range", "GET", "filter"},
		{"", "", "/api/User?filter=firstName:Valid,lastName:User,gender:male", "Filter by multiple strings and enum", "GET", "filter"},
		{"", "", "/api/User?filter=gender:female,netWorth:gte:70000,isAccountOwner:false", "Filter by enum, currency range, and boolean", "GET", "filter"},
		{"", "", "/api/User?filter=dob:gte:1950-01-01,dob:lt:2000-01-01,gender:male", "Filter by broader date range and gender", "GET", "filter"},
		{"", "", "/api/User?filter=netWorth:gte:-10000,isAccountOwner:true,gender:male", "Filter by netWorth (including negatives), account owner, and gender", "GET", "filter"},

		// Edge cases and special values
		{"", "", "/api/User?filter=firstName:NonExistent", "Filter by non-existent value", "GET", "filter"},
		{"", "", "/api/User?filter=netWorth:0", "Filter by zero netWorth", "GET", "filter"},
		{"", "", "/api/User?filter=dob:2050-01-01", "Filter by future date (no matches)", "GET", "filter"},
		{"", "", "/api/User?filter=gender:male,gender:female", "Filter by contradictory values (edge case)", "GET", "filter"},

		// Individual user with filter parameter
		{"basic_valid_001", "primary_valid_001", "/api/User/basic_valid_001?filter=gender:male", "Get individual user with filter parameter", "GET", "filter"},
	}

	cm.TestCases = append(cm.TestCases, filterTests...)
}

// addCaseTests adds comprehensive case sensitivity tests
func (cm *CategoryMatrix) addCaseTests() {
	caseTests := []TestSpec{
		// Lowercase parameter names
		{"", "", "/api/User?pagesize=5", "pagesize parameter", "GET", "case"},
		{"", "", "/api/User?page=1&pagesize=3", "pagesize with page", "GET", "case"},
		{"", "", "/api/User?sort=firstname", "Sort by firstname", "GET", "case"},
		{"", "", "/api/User?sort=lastname,createdat:desc", "Sort by multiple fields", "GET", "case"},
		{"", "", "/api/User?sort=isaccountowner,firstname", "Sort by boolean and string", "GET", "case"},
		{"", "", "/api/User?filter=gender:female", "Filter by gender field", "GET", "case"},
		{"", "", "/api/User?filter=firstname:test", "Filter by firstname", "GET", "case"},
		{"", "", "/api/User?filter=isaccountowner:true", "Filter by boolean field", "GET", "case"},
		{"", "", "/api/User?filter=networth:gte:1000", "Filter networth greater than or equal", "GET", "case"},
		{"", "", "/api/User?filter=networth:gt:1000", "Filter networth greater than", "GET", "case"},
		{"", "", "/api/User?filter=networth:lt:100000", "Filter networth less than", "GET", "case"},
		{"", "", "/api/User?filter=networth:lte:100000", "Filter networth less than or equal", "GET", "case"},
		{"", "", "/api/User?filter=dob:gte:1990-01-01", "Filter date of birth greater than or equal", "GET", "case"},
		{"", "", "/api/User?filter=dob:lt:2000-01-01", "Filter date of birth less than", "GET", "case"},
		{"", "", "/api/User?filter=createdat:gte:2023-01-01", "Filter created date greater than or equal", "GET", "case"},
		{"", "", "/api/User?filter=createdat:lt:2024-01-01", "Filter created date less than", "GET", "case"},
		{"", "", "/api/User?filter=updatedat:gt:2023-06-01", "Filter updated date greater than", "GET", "case"},
		{"", "", "/api/User?filter=updatedat:lte:2024-12-31", "Filter updated date less than or equal", "GET", "case"},
		{"", "", "/api/User?filter=networth:gte:1000,networth:lt:100000", "Filter networth range", "GET", "case"},
		{"", "", "/api/User?filter=dob:gte:1985-01-01,dob:lt:1995-12-31", "Filter date range", "GET", "case"},
		{"", "", "/api/User?filter=networth:gte:1000,dob:lt:2000-01-01", "Filter networth and date", "GET", "case"},
		{"", "", "/api/User?filter=gender:female", "Filter with lowercase value", "GET", "case"},
		{"", "", "/api/User?filter=email:test@example.com", "Filter email with lowercase", "GET", "case"},

		// Mixed case parameter names
		{"", "", "/api/User?Page=1&PageSize=5", "Mixed case Page and PageSize", "GET", "case"},
		{"", "", "/api/User?PAGE=2&pageSIZE=10", "Uppercase PAGE and mixed pageSIZE", "GET", "case"},
		{"", "", "/api/User?Sort=firstName&Filter=gender:female", "Mixed case Sort and Filter", "GET", "case"},
		{"", "", "/api/User?SORT=lastName,-dob&FILTER=networth:gte:1000", "Uppercase SORT and FILTER", "GET", "case"},
		{"", "", "/api/User?Page=1&PageSize=3&Sort=netWorth&Filter=gender:female", "All mixed case parameters", "GET", "case"},

		// Combined parameters
		{"", "", "/api/User?page=1&pagesize=5&sort=firstname&filter=gender:female", "Combined parameters", "GET", "case"},
		{"", "", "/api/User?sort=lastname,dob:desc&filter=isaccountowner:true,gender:female", "Complex combination", "GET", "case"},
		{"", "", "/api/User?page=2&pagesize=10&sort=networth&filter=dob:gte:1990-01-01", "Complex pagination with ranges", "GET", "case"},
	}

	cm.TestCases = append(cm.TestCases, caseTests...)
}

// addComboTests adds complex parameter combination tests
func (cm *CategoryMatrix) addComboTests() {
	comboTests := []TestSpec{
		// View + Sort combinations
		{"", "", "/api/User?view=account(id)&sort=firstName", "View with sort", "GET", "combo"},
		{"", "", "/api/User?view=account(id,name)&sort=netWorth:desc", "View with desc sort", "GET", "combo"},

		// View + Filter combinations
		{"", "", "/api/User?view=account(id)&filter=gender:male", "View with filter", "GET", "combo"},
		{"", "", "/api/User?view=account(id)&filter=netWorth:gte:50000", "View with range filter", "GET", "combo"},

		// View + Pagination combinations
		{"", "", "/api/User?view=account(id)&page=1&pageSize=3", "View with pagination", "GET", "combo"},
		{"", "", "/api/User?view=account(id,name)&pageSize=5", "View with page size", "GET", "combo"},

		// Sort + Filter combinations
		{"", "", "/api/User?sort=firstName&filter=gender:female", "Sort with filter", "GET", "combo"},
		{"", "", "/api/User?sort=netWorth:desc&filter=isAccountOwner:true", "Sort desc with boolean filter", "GET", "combo"},

		// Sort + Pagination combinations
		{"", "", "/api/User?sort=createdAt:desc&page=1&pageSize=5", "Sort with pagination", "GET", "combo"},
		{"", "", "/api/User?sort=firstName,lastName&pageSize=10", "Multi-sort with pagination", "GET", "combo"},

		// Filter + Pagination combinations
		{"", "", "/api/User?filter=gender:male&page=1&pageSize=5", "Filter with pagination", "GET", "combo"},
		{"", "", "/api/User?filter=netWorth:gte:40000&pageSize=3", "Range filter with pagination", "GET", "combo"},

		// All parameters combined
		{"", "", "/api/User?view=account(id)&sort=firstName&filter=gender:male&pageSize=3", "All parameters: view + sort + filter + pagination", "GET", "combo"},
		{"", "", "/api/User?view=account(id,name)&sort=netWorth:desc,firstName&filter=isAccountOwner:true,netWorth:gte:30000&page=1&pageSize=5", "Complex all parameters", "GET", "combo"},

		// Case variations in combinations
		{"", "", "/api/User?VIEW=account(id)&SORT=firstName&FILTER=gender:male", "Uppercase parameter combinations", "GET", "combo"},
		{"", "", "/api/User?view=Account(ID)&sort=FirstName&filter=Gender:male", "Mixed case field combinations", "GET", "combo"},
	}

	cm.TestCases = append(cm.TestCases, comboTests...)
}

// addIndividualViewTests adds individual user + view edge cases
func (cm *CategoryMatrix) addIndividualViewTests() {
	individualTests := []TestSpec{
		{"basic_valid_001", "primary_valid_001", "/api/User/basic_valid_001?view=account(createdAt,expiredAt)", "Individual user with extended view", "GET", "view_individual"},
		{"view_expired_fk_001", "expired_invalid_001", "/api/User/view_expired_fk_001?view=account(id,createdAt)", "User with bad FK + extended view", "GET", "view_individual"},
		{"", "", "/api/User/nonexistent_user_123456?view=account(id)", "Non-existent user with view", "GET", "view_individual"},
		{"basic_valid_001", "primary_valid_001", "/api/User/basic_valid_001?view=badentity(id)", "Individual user with bad view entity", "GET", "view_individual"},
		{"basic_invalid_enum_001", "primary_valid_001", "/api/User/basic_invalid_enum_001?view=account(createdAt,expiredAt)", "User with errors + extended view", "GET", "view_individual"},
	}

	cm.TestCases = append(cm.TestCases, individualTests...)
}

// addViewComboTests adds view + parameter combination tests
func (cm *CategoryMatrix) addViewComboTests() {
	viewComboTests := []TestSpec{
		{"", "", "/api/User?view=account(id)&sort=firstName", "View with sort", "GET", "view_combo"},
		{"", "", "/api/User?view=account(id,createdAt)&sort=netWorth:desc", "View with desc sort", "GET", "view_combo"},
		{"", "", "/api/User?view=account(id)&filter=gender:male", "View with filter", "GET", "view_combo"},
		{"", "", "/api/User?view=account(id)&filter=netWorth:gte:50000", "View with range filter", "GET", "view_combo"},
		{"", "", "/api/User?view=account(id)&sort=firstName&filter=gender:female", "View with sort and filter", "GET", "view_combo"},
		{"", "", "/api/User?view=account(id)&sort=dob:desc&filter=isAccountOwner:true", "View with desc sort and boolean filter", "GET", "view_combo"},
		{"", "", "/api/User?view=account(id)&sort=firstName&filter=gender:male&pageSize=3", "All parameters: view + sort + filter + pagination", "GET", "view_combo"},
		{"", "", "/api/User?view=account(id,createdAt)&sort=dob:desc,firstName&filter=isAccountOwner:true,netWorth:gte:0&page=1&pageSize=2", "Complex all parameters", "GET", "view_combo"},
	}

	cm.TestCases = append(cm.TestCases, viewComboTests...)
}

// addInvalidFieldTests adds tests for invalid field names
func (cm *CategoryMatrix) addInvalidFieldTests() {
	invalidTests := []TestSpec{
		{"", "", "/api/User?sort=invalidField", "Sort by invalid field name", "GET", "invalid"},
		{"", "", "/api/User?sort=firstName,badField", "Sort by valid and invalid fields", "GET", "invalid"},
		{"", "", "/api/User?filter=nonExistentField:test", "Filter by invalid field name", "GET", "invalid"},
		{"", "", "/api/User?filter=gender:male,invalidField:value", "Filter by valid and invalid fields", "GET", "invalid"},
		{"", "", "/api/User?sort=badSort&filter=badFilter:value", "Sort and filter with invalid fields", "GET", "invalid"},
		{"", "", "/api/User?sort=firstName,invalidField&filter=gender:female,badField:test", "Mixed valid and invalid sort/filter", "GET", "invalid"},
	}

	cm.TestCases = append(cm.TestCases, invalidTests...)
}

// addMixedCaseFieldTests adds comprehensive mixed case field name tests
func (cm *CategoryMatrix) addMixedCaseFieldTests() {
	mixedCaseTests := []TestSpec{
		{"", "", "/api/User?sort=FirstName", "Mixed case field in sort", "GET", "mixed_case"},
		{"", "", "/api/User?sort=LASTNAME:desc", "Uppercase field in sort", "GET", "mixed_case"},
		{"", "", "/api/User?sort=NetWorth,FirstName:desc", "Mixed case multiple sort fields", "GET", "mixed_case"},
		{"", "", "/api/User?filter=FirstName:Valid", "Mixed case field in filter", "GET", "mixed_case"},
		{"", "", "/api/User?filter=GENDER:male", "Uppercase field in filter", "GET", "mixed_case"},
		{"", "", "/api/User?filter=IsAccountOwner:true,NetWorth:gte:50000", "Mixed case multiple filter fields", "GET", "mixed_case"},
		{"", "", "/api/User?view=Account(ID,CreatedAt)", "Mixed case entity and fields in view", "GET", "mixed_case"},
		{"", "", "/api/User?view=ACCOUNT(id,CREATEDAT)", "Uppercase entity and fields in view", "GET", "mixed_case"},
	}

	cm.TestCases = append(cm.TestCases, mixedCaseTests...)
}