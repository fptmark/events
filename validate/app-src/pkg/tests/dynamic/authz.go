package dynamic

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"validate/pkg/types"
)

// testAuthzAdmin tests admin role with full permissions (cruds)
func testAuthzAdmin() (*types.TestResult, error) {
	return testAuthz("Admin", "12345678")
}

// testAuthzMgr tests manager role with no delete (crus)
func testAuthzMgr() (*types.TestResult, error) {
	return testAuthz("Mgr", "12345678")
}

// testAuthzRep tests representative role with read/update only (ru)
func testAuthzRep() (*types.TestResult, error) {
	return testAuthz("Rep", "12345678")
}

// testAuthz is the common authorization tester
// Tests all CRUD operations and compares actual results against expected permissions from DB
func testAuthz(username, password string) (*types.TestResult, error) {
	result := &types.TestResult{
		StatusCode: 200,
		Data:       []map[string]interface{}{},
		Issues:     []string{},
		Fields:     make(map[string][]interface{}),
		Passed:     false,
	}

	// Step 1: Login to get session cookie
	sessionID, loginResp, loginRespBody, err := LoginAs(username, password)
	if err != nil {
		return result, fmt.Errorf("login failed: %w", err)
	}

	if loginResp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Login failed for %s: got %d", username, loginResp.StatusCode))
		return result, nil
	}

	if sessionID == "" {
		result.Issues = append(result.Issues, "No sessionId cookie received")
		return result, nil
	}

	// Extract permissions from login response (now at top level via update_response)
	var loginData map[string]interface{}
	var permissions string
	if err := json.Unmarshal(loginRespBody, &loginData); err == nil {
		// Permissions are at top level of response now
		if permsData, ok := loginData["permissions"].(map[string]interface{}); ok {
			// permissions is like {"*": "cruds"}
			if permsStr, ok := permsData["*"].(string); ok {
				permissions = permsStr
			}
		}
	}

	if permissions == "" {
		result.Issues = append(result.Issues, "No permissions found in login response")
		return result, nil
	}

	// Step 2: Test CREATE operation (c)
	// Generate unique username/email to avoid conflicts on repeated runs
	timestamp := time.Now().UnixNano()
	uniqueUsername := fmt.Sprintf("authztest_%d", timestamp)
	uniqueEmail := fmt.Sprintf("authz_%d@test.com", timestamp)

	hasCreate := strings.ContainsRune(permissions, 'c')
	createStatus := ExecuteHTTPStatusOnly("/api/User", "POST", map[string]interface{}{
		"username":       uniqueUsername,
		"email":          uniqueEmail,
		"password":       "12345678",
		"firstName":      "Authz",
		"lastName":       "Test",
		"gender":         "other",
		"dob":            "2000-01-01",
		"isAccountOwner": true,
		"accountId":      "acc_valid_001",
		"netWorth":       50000,
	}, sessionID)
	checkPermission(result, "CREATE", hasCreate, createStatus)

	// Step 3: Test READ operation (r)
	hasRead := strings.ContainsRune(permissions, 'r')
	readStatus := ExecuteHTTPStatusOnly("/api/User/usr_get_001", "GET", nil, sessionID)
	checkPermission(result, "READ", hasRead, readStatus)

	// Step 4: Test UPDATE operation (u)
	hasUpdate := strings.ContainsRune(permissions, 'u')
	updateStatus := ExecuteHTTPStatusOnly("/api/User/usr_update_001", "PUT", map[string]interface{}{
		"username":       "usr_update_001",
		"email":          "update@test.com",
		"password":       "12345678",
		"firstName":      "Updated",
		"lastName":       "User",
		"isAccountOwner": false,
		"accountId":      "acc_valid_001",
	}, sessionID)
	checkPermission(result, "UPDATE", hasUpdate, updateStatus)

	// Step 5: Test DELETE operation (d)
	hasDelete := strings.ContainsRune(permissions, 'd')
	deleteStatus := ExecuteHTTPStatusOnly("/api/User/usr_delete_002", "DELETE", nil, sessionID)
	checkPermission(result, "DELETE", hasDelete, deleteStatus)

	// Step 6: Logout
	ExecuteHTTP("/api/logout", "POST", nil, sessionID)

	// Create summary data
	result.Data = []map[string]interface{}{
		{
			"user":         username,
			"permissions":  permissions,
			"createStatus": createStatus,
			"readStatus":   readStatus,
			"updateStatus": updateStatus,
			"deleteStatus": deleteStatus,
		},
	}

	result.Passed = len(result.Issues) == 0
	return result, nil
}

// checkPermission validates if the operation result matches expectations
func checkPermission(result *types.TestResult, operation string, hasPermission bool, actualStatus int) {
	var expectedStatus int
	if hasPermission {
		// CREATE operations return 201 Created, others return 200 OK
		if operation == "CREATE" {
			expectedStatus = 201
		} else {
			expectedStatus = 200
		}
	} else {
		expectedStatus = 403
	}

	if actualStatus != expectedStatus {
		result.Issues = append(result.Issues, fmt.Sprintf("%s: expected %d, got %d", operation, expectedStatus, actualStatus))
	}
}
