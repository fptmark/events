package dynamic

import (
	"encoding/json"
	"fmt"
	"sort"
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

	// Extract permissions from login response (expanded format)
	var loginData map[string]interface{}
	var actualPerms map[string]interface{}
	var permissions string
	if err := json.Unmarshal(loginRespBody, &loginData); err == nil {
		// Navigate to data.permissions
		if data, ok := loginData["data"].(map[string]interface{}); ok {
			if permsData, ok := data["permissions"].(map[string]interface{}); ok {
				actualPerms = permsData
				if entityPerms, ok := permsData["entity"].(map[string]interface{}); ok {
					// Get User entity permissions (e.g., "cru")
					if permsStr, ok := entityPerms["User"].(string); ok {
						permissions = permsStr
					}
				}
			}
		}
	}

	if permissions == "" {
		result.Issues = append(result.Issues, "No User permissions found in login response")
		return result, nil
	}

	// VERIFY PERMISSIONS STRUCTURE - Compare actual vs expected expansion
	expectedPerms, err := computeExpectedPermissions(username, sessionID)
	if err != nil {
		result.Issues = append(result.Issues, fmt.Sprintf("Failed to compute expected permissions: %v", err))
	} else {
		verifyIssues := verifyPermissionsStructure(username, actualPerms, expectedPerms)
		result.Issues = append(result.Issues, verifyIssues...)
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

// computeExpectedPermissions fetches role and computes expected permissions structure
func computeExpectedPermissions(username, sessionID string) (map[string]interface{}, error) {
	// Step 1: Get metadata entities
	_, metadataBody, err := ExecuteHTTP("/api/metadata", "GET", nil, sessionID)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch metadata: %w", err)
	}

	var metadataData map[string]interface{}
	if err := json.Unmarshal(metadataBody, &metadataData); err != nil {
		return nil, fmt.Errorf("failed to parse metadata: %w", err)
	}

	entities := []string{}
	if entitiesMap, ok := metadataData["entities"].(map[string]interface{}); ok {
		for entityName := range entitiesMap {
			entities = append(entities, entityName)
		}
	}
	sort.Strings(entities)

	// Step 2: Get user's auth record to find roleId
	authURL := fmt.Sprintf("/api/Auth?filter=name:%s", username)
	_, authBody, err := ExecuteHTTP(authURL, "GET", nil, sessionID)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch auth record: %w", err)
	}

	var authData map[string]interface{}
	if err := json.Unmarshal(authBody, &authData); err != nil {
		return nil, fmt.Errorf("failed to parse auth response: %w", err)
	}

	roleId := ""
	if data, ok := authData["data"].([]interface{}); ok && len(data) > 0 {
		if authRecord, ok := data[0].(map[string]interface{}); ok {
			roleId = authRecord["roleId"].(string)
		}
	}

	if roleId == "" {
		return nil, fmt.Errorf("roleId not found for user %s", username)
	}

	// Step 3: Get role record to get raw permissions
	roleURL := fmt.Sprintf("/api/Role/%s", roleId)
	_, roleBody, err := ExecuteHTTP(roleURL, "GET", nil, sessionID)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch role record: %w", err)
	}

	var roleData map[string]interface{}
	if err := json.Unmarshal(roleBody, &roleData); err != nil {
		return nil, fmt.Errorf("failed to parse role response: %w", err)
	}

	rawPermsJSON := ""
	if data, ok := roleData["data"].(map[string]interface{}); ok {
		rawPermsJSON = data["permissions"].(string)
	}

	if rawPermsJSON == "" {
		return nil, fmt.Errorf("permissions not found in role %s", roleId)
	}

	// Step 4: Expand permissions using same logic as server
	return expandPermissions(rawPermsJSON, entities)
}

// expandPermissions replicates server's permission expansion logic
func expandPermissions(rawPermsJSON string, entities []string) (map[string]interface{}, error) {
	var rawPerms map[string]string
	if err := json.Unmarshal([]byte(rawPermsJSON), &rawPerms); err != nil {
		return nil, fmt.Errorf("failed to parse raw permissions: %w", err)
	}

	dashboard := []string{}
	entityPerms := make(map[string]string)

	for _, entity := range entities {
		perm := ""

		// Check for specific entity permission (case-insensitive)
		for key, value := range rawPerms {
			if strings.ToLower(key) == strings.ToLower(entity) {
				perm = value
				break
			}
		}

		// If no specific permission, use wildcard
		if perm == "" {
			if wildcardPerm, ok := rawPerms["*"]; ok {
				perm = wildcardPerm
			}
		}

		// Only include entities with non-empty permissions
		if perm != "" {
			dashboard = append(dashboard, entity)
			entityPerms[entity] = perm
		}
	}

	return map[string]interface{}{
		"dashboard": dashboard,
		"entity":    entityPerms,
		"reports":   []interface{}{},
	}, nil
}

// verifyPermissionsStructure validates actual permissions match expected expansion
func verifyPermissionsStructure(username string, actual map[string]interface{}, expected map[string]interface{}) []string {
	issues := []string{}

	// Compare dashboard arrays (order-independent)
	actualDash, ok1 := actual["dashboard"].([]interface{})
	expectedDash, ok2 := expected["dashboard"].([]string)
	if !ok1 || !ok2 {
		issues = append(issues, fmt.Sprintf("%s: dashboard field type mismatch", username))
	} else {
		actualSet := make(map[string]bool)
		for _, e := range actualDash {
			if entity, ok := e.(string); ok {
				actualSet[entity] = true
			}
		}

		expectedSet := make(map[string]bool)
		for _, entity := range expectedDash {
			expectedSet[entity] = true
		}

		// Check for missing entities
		for entity := range expectedSet {
			if !actualSet[entity] {
				issues = append(issues, fmt.Sprintf("%s: dashboard missing entity '%s'", username, entity))
			}
		}

		// Check for extra entities
		for entity := range actualSet {
			if !expectedSet[entity] {
				issues = append(issues, fmt.Sprintf("%s: dashboard has extra entity '%s'", username, entity))
			}
		}
	}

	// Compare entity permissions map
	actualEntity, ok1 := actual["entity"].(map[string]interface{})
	expectedEntity, ok2 := expected["entity"].(map[string]string)
	if !ok1 || !ok2 {
		issues = append(issues, fmt.Sprintf("%s: entity field type mismatch", username))
	} else {
		// Check expected permissions exist and match
		for entity, expectedPerm := range expectedEntity {
			if actualPerm, ok := actualEntity[entity]; ok {
				if actualPerm.(string) != expectedPerm {
					issues = append(issues, fmt.Sprintf("%s: entity '%s' has '%s', expected '%s'",
						username, entity, actualPerm, expectedPerm))
				}
			} else {
				issues = append(issues, fmt.Sprintf("%s: entity permissions missing '%s'", username, entity))
			}
		}

		// Check for extra permissions
		for entity := range actualEntity {
			if _, ok := expectedEntity[entity]; !ok {
				issues = append(issues, fmt.Sprintf("%s: entity permissions has extra '%s'", username, entity))
			}
		}
	}

	// Compare reports (should both be empty for now)
	actualReports, ok1 := actual["reports"].([]interface{})
	expectedReports, ok2 := expected["reports"].([]interface{})
	if !ok1 || !ok2 {
		issues = append(issues, fmt.Sprintf("%s: reports field type mismatch", username))
	} else if len(actualReports) != len(expectedReports) {
		issues = append(issues, fmt.Sprintf("%s: reports length mismatch: got %d, expected %d",
			username, len(actualReports), len(expectedReports)))
	}

	return issues
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
