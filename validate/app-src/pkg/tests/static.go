package tests

import (
	"validate/pkg/types"
)

// GetAllTestCases returns all test cases with corrected IDs and schema-compliant definitions
// Ordered by progressive complexity: Basic CRUD → Parameterized Single-Entity GET → Collections
func GetAllTestCases() []types.TestCase {
	testCases := []types.TestCase{
		// =============================================================================
		// PHASE 1: BASIC CRUD - Simple individual entity operations
		// =============================================================================

		// Basic GET - Individual entity retrieval
		{Method: "GET", URL: "/api/User/usr_get_001", TestClass: "basic", Description: "Get valid user by ID", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User/usr_get_002", TestClass: "basic", Description: "Get another valid user by ID", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User/usr_nonexist_001", TestClass: "basic", Description: "Get non-existent user", ExpectedStatus: 404},
		{Method: "GET", URL: "/api/Account/acc_valid_001", TestClass: "basic", Description: "Get valid account by ID", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/Account/acc_nonexist_001", TestClass: "basic", Description: "Get non-existent account", ExpectedStatus: 404},

		// POST USER - SUCCESS CASES
		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user with all fields", ExpectedStatus: 201,
			RequestBody: map[string]interface{}{
				"firstName": "CreateTest", "lastName": "User", "email": "createtest@example.com",
				"username": "createtest_user", "gender": "male", "isAccountOwner": true,
				"netWorth": 50000, "dob": "1990-01-01", "password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "firstName", "lastName", "email", "username", "createdAt"},
			}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user with minimal required fields", ExpectedStatus: 201,
			RequestBody: map[string]interface{}{
				"firstName": "Minimal", "lastName": "User", "email": "minimal@example.com",
				"username": "minimal_user", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "firstName", "lastName", "email", "username", "createdAt"},
			}},

		// POST USER - VALIDATION FAILURES (422)
		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - missing firstName", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"lastName": "User", "email": "test@example.com",
				"username": "test_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - missing lastName", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "email": "test@example.com",
				"username": "test_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - missing email", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User",
				"username": "test_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - missing username", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "test@example.com",
				"password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - missing password", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "test_user", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - missing accountId", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "test_user", "password": "TestPass123!", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - missing isAccountOwner", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "test_user", "password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - invalid gender enum", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "invalidenum@example.com",
				"username": "invalid_enum_user", "gender": "invalid_gender", "password": "TestPass123!",
				"accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - username too short (< 3 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "shortuser@example.com",
				"username": "ab", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - username too long (> 50 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "longuser@example.com",
				"username": "this_username_is_way_too_long_and_exceeds_the_maximum_allowed_length_of_fifty_characters",
				"password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - email too short (< 8 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "a@b.co",
				"username": "short_email_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - email too long (> 50 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User",
				"email":    "this.is.a.very.long.email.address.that.exceeds@themaximumlengthallowed.com",
				"username": "long_email_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - invalid email format", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "not-an-email",
				"username": "invalid_email_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - password too short (< 8 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "shortpw@example.com",
				"username": "short_password_user", "password": "short", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - firstName too short (< 3 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "AB", "lastName": "User", "email": "shortfirst@example.com",
				"username": "short_firstname_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - firstName too long (> 100 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "ThisIsAnExtremelyLongFirstNameThatExceedsTheMaximumAllowedLengthOfOneHundredCharactersAndShouldFailValidationForSure",
				"lastName":  "User", "email": "longfirst@example.com",
				"username": "long_firstname_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - lastName too short (< 3 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "AB", "email": "shortlast@example.com",
				"username": "short_lastname_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - lastName too long (> 100 chars)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test",
				"lastName":  "ThisIsAnExtremelyLongLastNameThatExceedsTheMaximumAllowedLengthOfOneHundredCharactersAndShouldFailValidationForSure",
				"email":     "longlast@example.com",
				"username":  "long_lastname_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - netWorth out of range (> 10000000)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "toorich@example.com",
				"username": "too_rich_user", "password": "TestPass123!", "accountId": "acc_valid_001",
				"isAccountOwner": false, "netWorth": 99999999999},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - netWorth negative (< 0)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "negative@example.com",
				"username": "negative_wealth_user", "password": "TestPass123!", "accountId": "acc_valid_001",
				"isAccountOwner": false, "netWorth": -1000},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - invalid date format", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "baddate@example.com",
				"username": "bad_date_user", "password": "TestPass123!", "accountId": "acc_valid_001",
				"isAccountOwner": false, "dob": "not-a-date"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - empty string for required field", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "", "lastName": "User", "email": "emptyfield@example.com",
				"username": "empty_field_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - wrong type for isAccountOwner", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "wrongtype@example.com",
				"username": "wrong_type_user", "password": "TestPass123!", "accountId": "acc_valid_001",
				"isAccountOwner": "true"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - invalid FK (nonexistent account)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Test", "lastName": "User", "email": "invalidfk@example.com",
				"username": "invalid_fk_user", "password": "TestPass123!", "accountId": "acc_nonexist_999",
				"isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		// POST combo validation tests (validation takes precedence over constraints)
		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - bad enum + duplicate username (validation wins)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Combo", "lastName": "Test", "email": "combo1@example.com",
				"username": "duplicate_username", "password": "TestPass123!", "accountId": "acc_valid_001",
				"gender": "invalid_value", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - bad data + invalid FK (validation wins)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Combo", "lastName": "Test", "email": "combo2@example.com",
				"username": "combo_user_2", "password": "TestPass123!", "accountId": "acc_nonexist_999",
				"gender": "invalid_gender", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user - duplicate email + invalid FK (fk validation wins)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"firstName": "Combo", "lastName": "Test", "email": "duplicate@example.com",
				"username": "combo_user_3", "password": "TestPass123!", "accountId": "acc_nonexist_999",
				"gender": "male", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "constraint"}},

		// POST USER - DUPLICATE CONSTRAINT TESTS (409)
		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user for duplicate username test (should succeed)", ExpectedStatus: 201,
			RequestBody: map[string]interface{}{
				"firstName": "DupTest", "lastName": "User", "email": "dupuser1@example.com",
				"username": "duplicate_username", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user with duplicate username (should fail)", ExpectedStatus: 409,
			RequestBody: map[string]interface{}{
				"firstName": "Another", "lastName": "User", "email": "dupuser2@example.com",
				"username": "duplicate_username", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "constraint"}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user for duplicate email test (should succeed)", ExpectedStatus: 201,
			RequestBody: map[string]interface{}{
				"firstName": "EmailTest", "lastName": "User", "email": "duplicate@example.com",
				"username": "email_test_user1", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false}},

		{Method: "POST", URL: "/api/User", TestClass: "create", Description: "Create user with duplicate email (should fail)", ExpectedStatus: 409,
			RequestBody: map[string]interface{}{
				"firstName": "Another", "lastName": "User", "email": "duplicate@example.com",
				"username": "email_test_user2", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "constraint"}},

		// PUT USER - SUCCESS CASES
		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user with valid data", ExpectedStatus: 200,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Updated", "lastName": "UserName", "email": "updated@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"netWorth": 75000, "dob": "1990-01-01", "password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{
				ExpectedFields:      map[string]interface{}{"firstName": "Updated", "lastName": "UserName", "netWorth": float64(75000)},
				ShouldContainFields: []string{"id", "updatedAt"},
			}},

		{Method: "PUT", URL: "/api/User/usr_update_002", TestClass: "update", Description: "Update user with minimal fields", ExpectedStatus: 200,
			RequestBody: map[string]interface{}{
				"id": "usr_update_002", "firstName": "Minimal", "lastName": "Update", "email": "minupdate@example.com",
				"username": "usr_update_002", "isAccountOwner": true,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "updatedAt"},
			}},

		// PUT USER - VALIDATION FAILURES (422)
		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - invalid gender", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_001", "gender": "invalid_gender", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - username too long", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "this_updated_username_is_way_too_long_and_exceeds_the_maximum_allowed_length", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - invalid email format", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "not-valid-email",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - netWorth out of range", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"netWorth": 99999999999, "password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - invalid FK", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_nonexist_999"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - username too short", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "ab", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - email too short", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "a@b.co",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - email exceeds max", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User",
				"email":    "this.is.a.very.long.email.address.that.exceeds@themaximumlengthallowed.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - firstName too short", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "AB", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - firstName exceeds max", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id":        "usr_update_001",
				"firstName": "ThisIsAnExtremelyLongFirstNameThatExceedsTheMaximumAllowedLengthOfOneHundredCharactersAndShouldFailValidationForSure",
				"lastName":  "User", "email": "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - lastName too short", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "AB", "email": "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - lastName exceeds max", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test",
				"lastName": "ThisIsAnExtremelyLongLastNameThatExceedsTheMaximumAllowedLengthOfOneHundredCharactersAndShouldFailValidationForSure",
				"email":    "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - isAccountOwner wrong type", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": "false",
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - invalid date format", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"dob": "not-a-valid-date", "password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		// PUT USER - CONSTRAINT FAILURES (409)
		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - duplicate username", ExpectedStatus: 409,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_002", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "constraint"}},

		// {Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - duplicate email", ExpectedStatus: 409,
		// 	RequestBody: map[string]interface{}{
		// 		"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "updated2@example.com",
		// 		"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
		// 		"password": "TestPass123!", "accountId": "acc_valid_001"},
		// 	ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "constraint"}},

		// PUT combo validation tests
		{Method: "PUT", URL: "/api/User/usr_nonexist_999", TestClass: "update", Description: "Update non-existent user with bad data (422 wins)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_nonexist_999", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "nonexistent_999", "gender": "invalid_value", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - bad enum + duplicate username (validation wins)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_002", "gender": "invalid_gender", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		{Method: "PUT", URL: "/api/User/usr_update_001", TestClass: "update", Description: "Update user - bad data + invalid FK (validation wins)", ExpectedStatus: 422,
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "Test", "lastName": "User", "email": "test@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"netWorth": "not_a_number", "password": "TestPass123!", "accountId": "acc_nonexist_999"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "validation"}},

		// PUT USER - NOT FOUND (404)
		{Method: "PUT", URL: "/api/User/usr_nonexist_999", TestClass: "update", Description: "Update non-existent user", ExpectedStatus: 404,
			RequestBody: map[string]interface{}{
				"id": "usr_nonexist_999", "firstName": "NonExistent", "lastName": "Update", "email": "nonexist@example.com",
				"username": "nonexistent_999", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"},
			ExpectedData: &types.CRUDExpectation{ExpectedErrorType: "not_found"}},

		// DELETE USER
		{Method: "DELETE", URL: "/api/User/usr_delete_001", TestClass: "delete", Description: "Delete existing user", ExpectedStatus: 200},
		{Method: "DELETE", URL: "/api/User/usr_nonexist_999", TestClass: "delete", Description: "Delete non-existent user (idempotent)", ExpectedStatus: 200},

		// POST ACCOUNT - SUCCESS
		{Method: "POST", URL: "/api/Account", TestClass: "create", Description: "Create account with minimal fields", ExpectedStatus: 201,
			RequestBody: map[string]interface{}{},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "createdAt", "updatedAt"},
			}},

		{Method: "POST", URL: "/api/Account", TestClass: "create", Description: "Create account with expiredAt", ExpectedStatus: 201,
			RequestBody: map[string]interface{}{
				"expiredAt": "2025-12-31"},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "createdAt", "updatedAt", "expiredAt"},
			}},

		// PUT ACCOUNT - SUCCESS
		{Method: "PUT", URL: "/api/Account/acc_update_001", TestClass: "update", Description: "Update account with expiredAt", ExpectedStatus: 200,
			RequestBody: map[string]interface{}{
				"expiredAt": "2026-01-01"},
			ExpectedData: &types.CRUDExpectation{
				ShouldContainFields: []string{"id", "updatedAt"},
			}},

		// DELETE ACCOUNT
		{Method: "DELETE", URL: "/api/Account/acc_delete_001", TestClass: "delete", Description: "Delete existing account", ExpectedStatus: 200},
		{Method: "DELETE", URL: "/api/Account/acc_nonexist_999", TestClass: "delete", Description: "Delete non-existent account (idempotent)", ExpectedStatus: 200},

		// =============================================================================
		// PHASE 2: PARAMETERIZED SINGLE-ENTITY GET - Query parameters on specific entities
		// =============================================================================

		// VIEW (FK EXPANSION) TESTS - Account only has: id, expiredAt, createdAt, updatedAt
		{Method: "GET", URL: "/api/User/usr_view_001?view=account(id)", TestClass: "view", Description: "Get user with account ID view"},
		{Method: "GET", URL: "/api/User/usr_view_001?view=account(id,createdAt)", TestClass: "view", Description: "Get user with account view"},
		{Method: "GET", URL: "/api/User/usr_view_001?view=account(id,createdAt,updatedAt)", TestClass: "view", Description: "Get user with full account view"},
		{Method: "GET", URL: "/api/User/usr_view_002?view=account(id,createdAt)", TestClass: "view", Description: "Get different user with account view"},
		{Method: "GET", URL: "/api/User/usr_view_badfk_001?view=account(id)", TestClass: "view", Description: "Get user with invalid account FK"},
		{Method: "GET", URL: "/api/User/usr_view_nofk_001?view=account(id)", TestClass: "view", Description: "Get user with missing account FK"},
		{Method: "GET", URL: "/api/User/usr_view_001?view=account(nonexistent_field)", TestClass: "view", Description: "Get user with invalid view field", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User/usr_view_001?view=badentity(id)", TestClass: "view", Description: "Get user with bad view entity", ExpectedStatus: 400},

		// =============================================================================
		// PHASE 3: COLLECTION OPERATIONS - Multiple entities with parameters
		// =============================================================================

		// GET COLLECTION TESTS - List endpoints
		{Method: "GET", URL: "/api/User", TestClass: "basic", Description: "Get user list"},
		{Method: "GET", URL: "/api/user", TestClass: "basic", Description: "Get user list (lowercase entity)"},
		{Method: "GET", URL: "/api/Account", TestClass: "basic", Description: "Get account list"},

		// PAGINATION TESTS
		{Method: "GET", URL: "/api/User", TestClass: "page", Description: "Get user list with default pagination"},
		{Method: "GET", URL: "/api/User?pageSize=3", TestClass: "page", Description: "Get user list with page size 3"},
		{Method: "GET", URL: "/api/User?pageSize=5", TestClass: "page", Description: "Get user list with page size 5"},
		{Method: "GET", URL: "/api/User?page=1&pageSize=5", TestClass: "page", Description: "Get user list page 1 with size 5"},
		{Method: "GET", URL: "/api/User?page=2&pageSize=5", TestClass: "page", Description: "Get user list page 2 with size 5"},
		{Method: "GET", URL: "/api/User?page=3&pageSize=5", TestClass: "page", Description: "Get user list page 3 with size 5"},
		{Method: "GET", URL: "/api/User?page=1&pageSize=1", TestClass: "page", Description: "Get user list page 1 with size 1"},
		{Method: "GET", URL: "/api/User?page=2&pageSize=1", TestClass: "page", Description: "Get user list page 2 with size 1"},
		{Method: "GET", URL: "/api/User?page=10&pageSize=5", TestClass: "page", Description: "Get user list page 10 (beyond data)"},
		{Method: "GET", URL: "/api/User?pageSize=100", TestClass: "page", Description: "Get user list with large page size"},

		// SORTING TESTS
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

		// FILTERING TESTS
		{Method: "GET", URL: "/api/User?filter=firstName:James", TestClass: "filter", Description: "Filter by firstName contains James"},
		{Method: "GET", URL: "/api/User?filter=lastName:Smith", TestClass: "filter", Description: "Filter by lastName contains Smith"},
		{Method: "GET", URL: "/api/User?filter=gender:male", TestClass: "filter", Description: "Filter by gender male"},
		{Method: "GET", URL: "/api/User?filter=gender:female", TestClass: "filter", Description: "Filter by gender female"},
		{Method: "GET", URL: "/api/User?filter=gender:other", TestClass: "filter", Description: "Filter by gender other"},
		{Method: "GET", URL: "/api/User?filter=isAccountOwner:true", TestClass: "filter", Description: "Filter by isAccountOwner true"},
		{Method: "GET", URL: "/api/User?filter=isAccountOwner:false", TestClass: "filter", Description: "Filter by isAccountOwner false"},
		{Method: "GET", URL: "/api/User?filter=netWorth:gt:50000", TestClass: "filter", Description: "Filter by netWorth > 50k"},
		{Method: "GET", URL: "/api/User?filter=netWorth:gte:50000", TestClass: "filter", Description: "Filter by netWorth >= 50k"},
		{Method: "GET", URL: "/api/User?filter=netWorth:lt:100000", TestClass: "filter", Description: "Filter by netWorth < 100k"},
		{Method: "GET", URL: "/api/User?filter=netWorth:lte:100000", TestClass: "filter", Description: "Filter by netWorth <= 100k"},
		{Method: "GET", URL: "/api/User?filter=netWorth:eq:75000", TestClass: "filter", Description: "Filter by netWorth = 75k"},
		{Method: "GET", URL: "/api/User?filter=gender:male,isAccountOwner:true", TestClass: "filter", Description: "Filter by gender male and account owner"},
		{Method: "GET", URL: "/api/User?filter=gender:female,netWorth:gte:50000", TestClass: "filter", Description: "Filter by gender female and wealthy"},
		{Method: "GET", URL: "/api/User?filter=firstName:John,gender:male", TestClass: "filter", Description: "Filter by firstName and gender"},
		{Method: "GET", URL: "/api/User?filter=netWorth:gte:25000,netWorth:lte:75000", TestClass: "filter", Description: "Filter by netWorth range"},
		{Method: "GET", URL: "/api/User?filter=dob:1990-01-01", TestClass: "filter", Description: "Filter by exact date of birth"},
		{Method: "GET", URL: "/api/User?filter=dob:gt:1950-01-01", TestClass: "filter", Description: "Filter by DOB > 1950"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1950-01-01", TestClass: "filter", Description: "Filter by DOB >= 1950"},
		{Method: "GET", URL: "/api/User?filter=dob:lt:2000-01-01", TestClass: "filter", Description: "Filter by DOB < 2000"},
		{Method: "GET", URL: "/api/User?filter=dob:lte:2000-12-31", TestClass: "filter", Description: "Filter by DOB <= 2000"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1950-01-01,dob:lt:2000-01-01", TestClass: "filter", Description: "Date range filter"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1950-01-01,dob:lt:2000-01-01,gender:male", TestClass: "filter", Description: "Complex date and gender filter"},
		{Method: "GET", URL: "/api/User?filter=email:example.com", TestClass: "filter", Description: "Filter by email domain"},
		{Method: "GET", URL: "/api/User?filter=email:@gmail.com", TestClass: "filter", Description: "Filter by specific email domain"},
		{Method: "GET", URL: "/api/User?filter=username:James", TestClass: "filter", Description: "Filter by username"},
		{Method: "GET", URL: "/api/User?filter=createdAt:gte:2023-01-01", TestClass: "filter", Description: "Filter by createdAt >= 2023"},
		{Method: "GET", URL: "/api/User?filter=createdAt:lt:2024-01-01", TestClass: "filter", Description: "Filter by createdAt < 2024"},
		{Method: "GET", URL: "/api/User?filter=updatedAt:gt:2023-06-01", TestClass: "filter", Description: "Filter by updatedAt > June 2023"},
		{Method: "GET", URL: "/api/User?filter=updatedAt:lte:2024-12-31", TestClass: "filter", Description: "Filter by updatedAt <= 2024"},
		{Method: "GET", URL: "/api/User?filter=dob:1985-06-15", TestClass: "filter", Description: "Filter by specific DOB"},
		{Method: "GET", URL: "/api/User?filter=dob:1992-03-20", TestClass: "filter", Description: "Filter by another specific DOB"},
		{Method: "GET", URL: "/api/User?filter=dob:2050-01-01", TestClass: "filter", Description: "Filter by future DOB"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1985-01-01,dob:lt:1995-12-31", TestClass: "filter", Description: "DOB range filter narrow"},
		{Method: "GET", URL: "/api/User?filter=dob:gte:1950-01-01,dob:lte:2050-12-31", TestClass: "filter", Description: "DOB range filter wide"},
		{Method: "GET", URL: "/api/User?filter=networth:gt:1000", TestClass: "filter", Description: "Filter by networth (lowercase)"},
		{Method: "GET", URL: "/api/User?filter=networth:gte:1000", TestClass: "filter", Description: "Filter by networth gte (lowercase)"},
		{Method: "GET", URL: "/api/User?filter=isaccountowner:true", TestClass: "filter", Description: "Filter by isaccountowner (lowercase)"},

		// CASE INSENSITIVITY TESTS
		{Method: "GET", URL: "/api/User?pagesize=5", TestClass: "case", Description: "pagesize parameter (lowercase)"},
		{Method: "GET", URL: "/api/User?PAGESIZE=5", TestClass: "case", Description: "PAGESIZE parameter (uppercase)"},
		{Method: "GET", URL: "/api/User?PageSize=5", TestClass: "case", Description: "PageSize parameter (mixed case)"},
		{Method: "GET", URL: "/api/User?page=2&pagesize=3", TestClass: "case", Description: "Mixed case page and pagesize"},
		{Method: "GET", URL: "/api/User?sort=firstname", TestClass: "case", Description: "Sort by firstname (lowercase)"},
		{Method: "GET", URL: "/api/User?sort=FIRSTNAME", TestClass: "case", Description: "Sort by FIRSTNAME (uppercase)"},
		{Method: "GET", URL: "/api/User?sort=FirstName", TestClass: "case", Description: "Sort by FirstName (mixed case)"},
		{Method: "GET", URL: "/api/User?sort=lastname:desc", TestClass: "case", Description: "Sort by lastname desc (lowercase)"},
		{Method: "GET", URL: "/api/User?filter=firstname:James", TestClass: "case", Description: "Filter by firstname (lowercase)"},
		{Method: "GET", URL: "/api/User?filter=FIRSTNAME:James", TestClass: "case", Description: "Filter by FIRSTNAME (uppercase)"},
		{Method: "GET", URL: "/api/User?filter=FirstName:James", TestClass: "case", Description: "Filter by FirstName (mixed case)"},
		{Method: "GET", URL: "/api/User?filter=GENDER:male", TestClass: "case", Description: "Filter by GENDER (uppercase)"},
		{Method: "GET", URL: "/api/User?filter=gender:MALE", TestClass: "case", Description: "Filter by gender with MALE value"},
		{Method: "GET", URL: "/api/User?Page=1&PageSize=5", TestClass: "case", Description: "Mixed case Page and PageSize"},

		// View with collections
		{Method: "GET", URL: "/api/User?view=account(id)", TestClass: "view", Description: "Get user list with account ID view"},
		{Method: "GET", URL: "/api/User?view=account(id,createdAt,updatedAt)", TestClass: "view", Description: "Get user list with full account view"},
		{Method: "GET", URL: "/api/User?pageSize=3&view=account(id)", TestClass: "view", Description: "Get user list with pagination and view"},
		{Method: "GET", URL: "/api/User?pageSize=1&view=account(id,createdAt,updatedAt,expiredAt)", TestClass: "view", Description: "Get user list with all account fields"},

		// COMBO PARAMETER TESTS
		{Method: "GET", URL: "/api/User?view=account(id)&sort=firstName", TestClass: "combo", Description: "View with sort"},
		{Method: "GET", URL: "/api/User?view=account(id,createdAt)&sort=firstName:desc", TestClass: "combo", Description: "Account view with sort desc"},
		{Method: "GET", URL: "/api/User?view=account(id)&filter=gender:male", TestClass: "combo", Description: "View with filter"},
		{Method: "GET", URL: "/api/User?view=account(id,createdAt)&filter=gender:female", TestClass: "combo", Description: "Account view with filter"},
		{Method: "GET", URL: "/api/User?sort=firstName&filter=gender:female", TestClass: "combo", Description: "Sort with filter"},
		{Method: "GET", URL: "/api/User?sort=netWorth:desc&filter=isAccountOwner:true", TestClass: "combo", Description: "Sort by wealth with account owner filter"},
		{Method: "GET", URL: "/api/User?view=account(id)&sort=firstName&filter=gender:male", TestClass: "combo", Description: "View + sort + filter"},
		{Method: "GET", URL: "/api/User?view=account(id,createdAt)&sort=firstName&filter=gender:male", TestClass: "combo", Description: "Full view + sort + filter"},
		{Method: "GET", URL: "/api/User?view=account(id)&sort=firstName&filter=gender:male&pageSize=3", TestClass: "combo", Description: "All parameters: view + sort + filter + pagination"},
		{Method: "GET", URL: "/api/User?view=account(id,createdAt)&sort=netWorth:desc&filter=isAccountOwner:true&pageSize=2", TestClass: "combo", Description: "All parameters with wealth focus"},
		{Method: "GET", URL: "/api/User?view=account(id)&sort=lastName,firstName&filter=gender:female,netWorth:gte:50000&page=2&pageSize=3", TestClass: "combo", Description: "Complex multi-field combo"},

		// =============================================================================
		// EDGE CASES - Invalid parameters and error scenarios
		// =============================================================================
		{Method: "GET", URL: "/api/User?sort=invalidField", TestClass: "edge", Description: "Sort by invalid field", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?filter=invalidField:value", TestClass: "edge", Description: "Filter by invalid field", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?view=invalidEntity(id)", TestClass: "edge", Description: "View invalid entity", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?page=0", TestClass: "edge", Description: "Page 0 (invalid)", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?page=-1", TestClass: "edge", Description: "Negative page number", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?pageSize=0", TestClass: "edge", Description: "Page size 0", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?pageSize=-5", TestClass: "edge", Description: "Negative page size", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?pageSize=1000", TestClass: "edge", Description: "Very large page size"},
		{Method: "GET", URL: "/api/User?sort=", TestClass: "edge", Description: "Empty sort parameter"},
		{Method: "GET", URL: "/api/User?filter=", TestClass: "edge", Description: "Empty filter parameter"},
		{Method: "GET", URL: "/api/User?view=", TestClass: "edge", Description: "Empty view parameter"},
		{Method: "GET", URL: "/api/User?sort=firstName:invalid", TestClass: "edge", Description: "Invalid sort direction", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?filter=netWorth:invalid:50000", TestClass: "edge", Description: "Invalid filter operator", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?view=account()", TestClass: "edge", Description: "Empty view fields", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?view=account(invalidField)", TestClass: "edge", Description: "Invalid view field", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?unknown=parameter", TestClass: "edge", Description: "Unknown query parameter", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?sort=firstName&sort=lastName", TestClass: "edge", Description: "Duplicate sort parameters"},
		{Method: "GET", URL: "/api/User?filter=gender:male&filter=gender:female", TestClass: "edge", Description: "Duplicate filter parameters"},
		{Method: "GET", URL: "/api/User?view=account(id)&view=profile(name)", TestClass: "edge", Description: "Duplicate view parameters"},
		{Method: "GET", URL: "/api/User/", TestClass: "edge", Description: "Trailing slash on entity"},
		{Method: "GET", URL: "/api/User//", TestClass: "edge", Description: "Double slash in URL"},
		{Method: "GET", URL: "/api/User?%20invalid=space", TestClass: "edge", Description: "URL with special characters", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?sort=firstName%2Cdesc", TestClass: "edge", Description: "URL encoded sort parameter w encoded comma", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?sort=firstName%3Adesc", TestClass: "edge", Description: "URL encoded sort parameter w encoded colon"},
		{Method: "GET", URL: "/api/User?filter=firstName%3AJames", TestClass: "edge", Description: "URL encoded filter parameter"},
		{Method: "POST", URL: "/api/User?pageSize=5", TestClass: "edge", Description: "POST with query parameters", ExpectedStatus: 201,
			RequestBody: map[string]interface{}{
				"firstName": "EdgePost", "lastName": "User", "email": "edgepost@example.com",
				"username": "edge_post_user", "password": "TestPass123!", "accountId": "acc_valid_001", "isAccountOwner": false}},
		{Method: "PUT", URL: "/api/User/usr_update_001?sort=firstName", TestClass: "edge", Description: "PUT with query parameters",
			RequestBody: map[string]interface{}{
				"id": "usr_update_001", "firstName": "EdgeTest", "lastName": "User", "email": "edge@example.com",
				"username": "usr_update_001", "gender": "male", "isAccountOwner": false,
				"password": "TestPass123!", "accountId": "acc_valid_001"}},
		{Method: "DELETE", URL: "/api/User/usr_delete_edge_001?filter=gender:male", TestClass: "edge", Description: "DELETE with query parameters"},
		{Method: "GET", URL: "/api/User?sort=firstName,", TestClass: "edge", Description: "Sort with trailing comma"},
		{Method: "GET", URL: "/api/User?filter=gender:male,", TestClass: "edge", Description: "Filter with trailing comma"},
		{Method: "GET", URL: "/api/User?view=account(id,)", TestClass: "edge", Description: "View with trailing comma"},
		{Method: "GET", URL: "/api/User?sort=,firstName", TestClass: "edge", Description: "Sort with leading comma"},
		{Method: "GET", URL: "/api/User?filter=,gender:male", TestClass: "edge", Description: "Filter with leading comma"},

		// =============================================================================
		// FILTER MATCHING - Test exact vs contains matching modes
		// =============================================================================

		// Basic exact matching tests - single field
		{Method: "GET", URL: "/api/User?filter=username:mark&filter_match=full", TestClass: "filter", Description: "Filter username exact match - full value", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=username:mar&filter_match=full", TestClass: "filter", Description: "Filter username exact match - partial (no match)", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=username:mark&filter_match=substring", TestClass: "filter", Description: "Filter username contains - multiple results", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=username:mark", TestClass: "filter", Description: "Filter username default (contains)", ExpectedStatus: 200},

		{Method: "GET", URL: "/api/User?filter=firstName:James&filter_match=full", TestClass: "filter", Description: "Filter firstName exact match", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=firstName:Jam&filter_match=full", TestClass: "filter", Description: "Filter firstName exact - partial (no match)", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=firstName:James&filter_match=substring", TestClass: "filter", Description: "Filter firstName contains", ExpectedStatus: 200},

		{Method: "GET", URL: "/api/User?filter=lastName:Smith&filter_match=full", TestClass: "filter", Description: "Filter lastName exact match", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=lastName:Smi&filter_match=full", TestClass: "filter", Description: "Filter lastName exact - partial (no match)", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=lastName:Smith&filter_match=substring", TestClass: "filter", Description: "Filter lastName contains", ExpectedStatus: 200},

		{Method: "GET", URL: "/api/User?filter=email:example.com&filter_match=full", TestClass: "filter", Description: "Filter email exact - domain only (no match)", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=email:test@example.com&filter_match=full", TestClass: "filter", Description: "Filter email exact - full address", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=email:example.com&filter_match=substring", TestClass: "filter", Description: "Filter email contains - domain", ExpectedStatus: 200},

		// Exact matching on enum fields (should behave same as default)
		{Method: "GET", URL: "/api/User?filter=gender:male&filter_match=full", TestClass: "filter", Description: "Filter gender exact match", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=gender:female&filter_match=full", TestClass: "filter", Description: "Filter gender female exact match", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=gender:other&filter_match=full", TestClass: "filter", Description: "Filter gender other exact match", ExpectedStatus: 200},

		// Exact matching on boolean fields
		{Method: "GET", URL: "/api/User?filter=isAccountOwner:true&filter_match=full", TestClass: "filter", Description: "Filter isAccountOwner true exact", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=isAccountOwner:false&filter_match=full", TestClass: "filter", Description: "Filter isAccountOwner false exact", ExpectedStatus: 200},

		// Exact matching on numeric fields
		{Method: "GET", URL: "/api/User?filter=netWorth:50000&filter_match=full", TestClass: "filter", Description: "Filter netWorth exact value", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=netWorth:eq:50000&filter_match=full", TestClass: "filter", Description: "Filter netWorth eq with exact mode", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=netWorth:gt:50000&filter_match=full", TestClass: "filter", Description: "Filter netWorth gt with exact mode", ExpectedStatus: 200},

		// Exact matching on date fields
		{Method: "GET", URL: "/api/User?filter=dob:1990-01-01&filter_match=full", TestClass: "filter", Description: "Filter dob exact date", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=dob:gt:1990-01-01&filter_match=full", TestClass: "filter", Description: "Filter dob gt with exact mode", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=createdAt:gte:2023-01-01&filter_match=full", TestClass: "filter", Description: "Filter createdAt gte with exact mode", ExpectedStatus: 200},

		// Multi-field exact matching
		{Method: "GET", URL: "/api/User?filter=firstName:James,lastName:Smith&filter_match=full", TestClass: "filter", Description: "Filter multiple fields exact match", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=firstName:James,gender:male&filter_match=full", TestClass: "filter", Description: "Filter firstName and gender exact", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=gender:female,isAccountOwner:true&filter_match=full", TestClass: "filter", Description: "Filter gender and owner exact", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=username:mark,gender:male&filter_match=full", TestClass: "filter", Description: "Filter username and gender exact", ExpectedStatus: 200},

		// Exact matching combined with other parameters
		{Method: "GET", URL: "/api/User?filter=firstName:James&filter_match=full&sort=lastName", TestClass: "combo", Description: "Exact filter with sort", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=gender:male&filter_match=full&sort=netWorth:desc", TestClass: "combo", Description: "Exact filter with sort desc", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=firstName:James&filter_match=full&pageSize=5", TestClass: "combo", Description: "Exact filter with pagination", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=gender:female&filter_match=full&page=1&pageSize=3", TestClass: "combo", Description: "Exact filter with page and size", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=lastName:Smith&filter_match=full&view=account(id)", TestClass: "combo", Description: "Exact filter with view", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=gender:male&filter_match=full&view=account(id,createdAt)&sort=firstName", TestClass: "combo", Description: "Exact filter with view and sort", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=firstName:James,gender:male&filter_match=full&sort=netWorth:desc&pageSize=5", TestClass: "combo", Description: "Multi-field exact with sort and page", ExpectedStatus: 200},

		// Case sensitivity tests with exact matching
		{Method: "GET", URL: "/api/User?filter=firstName:james&filter_match=full", TestClass: "filter", Description: "Exact filter lowercase (case insensitive)", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=firstName:JAMES&filter_match=full", TestClass: "filter", Description: "Exact filter uppercase (case insensitive)", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=email:TEST@EXAMPLE.COM&filter_match=full", TestClass: "filter", Description: "Exact email uppercase", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=gender:MALE&filter_match=full", TestClass: "filter", Description: "Exact gender uppercase", ExpectedStatus: 200},

		// Invalid filter_matching values
		{Method: "GET", URL: "/api/User?filter=firstName:James&filter_match=invalid", TestClass: "edge", Description: "Invalid filter_matching value", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?filter=firstName:James&filter_match=", TestClass: "edge", Description: "Empty filter_matching value", ExpectedStatus: 200},
		{Method: "GET", URL: "/api/User?filter=firstName:James&filter_match=partial", TestClass: "edge", Description: "Unsupported filter_matching mode", ExpectedStatus: 400},

		// Case insensitivity for filter_matching parameter itself
		{Method: "GET", URL: "/api/User?filter=firstName:James&FILTER_MATCH=exact", TestClass: "case", Description: "FILTER_MATCH uppercase", ExpectedStatus: 400},
		{Method: "GET", URL: "/api/User?filter=firstName:James&Filter_Match=exact", TestClass: "case", Description: "Filter_Match mixed case", ExpectedStatus: 400},

		{Method: "GET", URL: "/api/User?view=account(,id)", TestClass: "edge", Description: "View with leading comma"},
		{Method: "GET", URL: "/api/User?sort=firstName,,lastName", TestClass: "edge", Description: "Sort with double comma"},
		{Method: "GET", URL: "/api/User?filter=gender:male,,isAccountOwner:true", TestClass: "edge", Description: "Filter with double comma"},
		{Method: "GET", URL: "/api/User?view=account(id,,createdAt)", TestClass: "edge", Description: "View with double comma"},
		{Method: "GET", URL: "/api/InvalidEntity", TestClass: "edge", Description: "Invalid entity endpoint", ExpectedStatus: 404},
		{Method: "GET", URL: "/api/NoSuchEntity", TestClass: "edge", Description: "Non-existent entity endpoint", ExpectedStatus: 404},
		{Method: "GET", URL: "/api/", TestClass: "edge", Description: "API root endpoint", ExpectedStatus: 404},
		{Method: "GET", URL: "/", TestClass: "edge", Description: "Root endpoint", ExpectedStatus: 404},
		{Method: "GET", URL: "/invalid-url", TestClass: "edge", Description: "Invalid URL path", ExpectedStatus: 404},

		// =============================================================================
		// DYNAMIC TESTS (Multi-step programmatic tests and admin endpoints)
		// =============================================================================
		{Method: "GET", URL: "testMetadata", TestClass: "dynamic", Description: "Get system metadata"},
		{Method: "GET", URL: "testDbReport", TestClass: "dynamic", Description: "Get database status report"},
		{Method: "GET", URL: "testDbInit", TestClass: "dynamic", Description: "Initialize database confirmation page"},
		{Method: "GET", URL: "testPaginationAggregation", TestClass: "dynamic", Description: "Aggregate pagination test"},
		{Method: "GET", URL: "testAuth", TestClass: "dynamic", Description: "Redis authentication workflow (login, refresh, logout)"},
	}

	// Add ID and set default ExpectedStatus
	for i := range testCases {
		testCases[i].ID = i + 1
		if testCases[i].ExpectedStatus == 0 {
			testCases[i].ExpectedStatus = 200
		}
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

// GetAllCategories returns a map of all test categories with initialized counters
func GetAllCategories() map[string]*types.CategoryStats {
	categories := make(map[string]*types.CategoryStats)

	for _, tc := range GetAllTestCases() {
		if _, exists := categories[tc.TestClass]; !exists {
			categories[tc.TestClass] = &types.CategoryStats{Success: 0, Failed: 0}
		}
	}

	return categories
}

// GetTestCategory returns the TestClass for a given test number (1-based)
func GetTestCategory(testNumber int) string {
	allTests := GetAllTestCases()
	if testNumber < 1 || testNumber > len(allTests) {
		return "unknown"
	}
	return allTests[testNumber-1].TestClass
}
