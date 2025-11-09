package dynamic

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"

	"validate/pkg/core"
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

	// Step 2: Get roleId from bootstrap auth data
	roleId, err := getRoleIdFromBootstrapAuth(username)
	if err != nil {
		result.Issues = append(result.Issues, fmt.Sprintf("Failed to get roleId from bootstrap: %v", err))
		return result, nil
	}

	// Step 3: Get permissions JSON from bootstrap role data
	rawPermsJSON, err := getPermissionsFromBootstrapRole(roleId)
	if err != nil {
		result.Issues = append(result.Issues, fmt.Sprintf("Failed to get permissions from bootstrap: %v", err))
		return result, nil
	}

	// Step 4: Get metadata entities
	_, metadataBody, err := ExecuteHTTP("/api/metadata", "GET", nil, sessionID)
	if err != nil {
		result.Issues = append(result.Issues, fmt.Sprintf("Failed to fetch metadata: %v", err))
		return result, nil
	}

	var metadataData map[string]interface{}
	if err := json.Unmarshal(metadataBody, &metadataData); err != nil {
		result.Issues = append(result.Issues, fmt.Sprintf("Failed to parse metadata: %v", err))
		return result, nil
	}

	entities := []string{}
	if entitiesMap, ok := metadataData["entities"].(map[string]interface{}); ok {
		for entityName := range entitiesMap {
			entities = append(entities, entityName)
		}
	}
	sort.Strings(entities)

	// Step 5: Expand permissions
	expectedPerms, err := expandPermissions(rawPermsJSON, entities)
	if err != nil {
		result.Issues = append(result.Issues, fmt.Sprintf("Failed to expand permissions: %v", err))
		return result, nil
	}

	// Step 6: Extract actual permissions from login response
	var loginData map[string]interface{}
	var actualPerms map[string]interface{}
	if err := json.Unmarshal(loginRespBody, &loginData); err == nil {
		if data, ok := loginData["data"].(map[string]interface{}); ok {
			if permsData, ok := data["permissions"].(map[string]interface{}); ok {
				actualPerms = permsData
			}
		}
	}

	if actualPerms == nil {
		result.Issues = append(result.Issues, "No permissions found in login response")
		return result, nil
	}

	// Debug output: Show raw, actual, and expected permissions for comparison
	result.Notes = append(result.Notes, fmt.Sprintf("Raw permissions from bootstrap: %s", rawPermsJSON))

	actualPermsJSON, _ := json.MarshalIndent(actualPerms, "  ", "  ")
	result.Notes = append(result.Notes, fmt.Sprintf("Actual permissions from login:\n  %s", string(actualPermsJSON)))

	expectedPermsJSON, _ := json.MarshalIndent(expectedPerms, "  ", "  ")
	result.Notes = append(result.Notes, fmt.Sprintf("Expected permissions (computed by test):\n  %s", string(expectedPermsJSON)))

	// Step 7: Compare expanded permissions vs login permissions, fail on mismatch
	verifyIssues := verifyPermissionsStructure(username, actualPerms, expectedPerms)
	result.Issues = append(result.Issues, verifyIssues...)

	// Step 8: Get User entity permissions for CRUD tests
	expectedUserPerms := ""
	if entityPerms, ok := expectedPerms["entity"].(map[string]string); ok {
		expectedUserPerms = entityPerms["User"]
	}

	// Step 9: Test CREATE operation (c)
	hasCreate := strings.ContainsRune(expectedUserPerms, 'c')

	timestamp := time.Now().UnixNano()
	uniqueUsername := fmt.Sprintf("authztest_%d", timestamp)
	uniqueEmail := fmt.Sprintf("authz_%d@test.com", timestamp)

	var createStatus int
	createEntity, err := types.NewEntity("User", map[string]interface{}{
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
	})
	if err != nil {
		result.Issues = append(result.Issues, fmt.Sprintf("Failed to create entity: %v", err))
		createStatus = 0
	} else {
		createStatus = ExecuteHTTPStatusOnly("/api/User", "POST", createEntity.ToJSON(), sessionID)
	}
	checkPermission(result, "CREATE", hasCreate, createStatus)

	// Step 4: Test READ operation (r)
	hasRead := strings.ContainsRune(expectedUserPerms, 'r')
	readStatus := ExecuteHTTPStatusOnly("/api/User/usr_get_001", "GET", nil, sessionID)
	checkPermission(result, "READ", hasRead, readStatus)

	// Step 5: Test UPDATE operation (u)
	hasUpdate := strings.ContainsRune(expectedUserPerms, 'u')

	var updateStatus int
	updateEntity, err := types.NewEntity("User", map[string]interface{}{
		"username":       "usr_update_001",
		"email":          "update@test.com",
		"password":       "12345678",
		"firstName":      "Updated",
		"lastName":       "User",
		"isAccountOwner": false,
		"accountId":      "acc_valid_001",
	})
	if err != nil {
		result.Issues = append(result.Issues, fmt.Sprintf("Failed to create update entity: %v", err))
		updateStatus = 0
	} else {
		updateStatus = ExecuteHTTPStatusOnly("/api/User/usr_update_001", "PUT", updateEntity.ToJSON(), sessionID)
	}
	checkPermission(result, "UPDATE", hasUpdate, updateStatus)

	// Step 6: Test DELETE operation (d)
	hasDelete := strings.ContainsRune(expectedUserPerms, 'd')
	deleteStatus := ExecuteHTTPStatusOnly("/api/User/usr_delete_002", "DELETE", nil, sessionID)
	checkPermission(result, "DELETE", hasDelete, deleteStatus)

	// Step 10: Logout
	ExecuteHTTP("/api/logout", "POST", nil, sessionID)

	// Get actual User permissions from login response for summary
	actualUserPerms := ""
	if entityPerms, ok := actualPerms["entity"].(map[string]interface{}); ok {
		if permsStr, ok := entityPerms["User"].(string); ok {
			actualUserPerms = permsStr
		}
	}

	// Create summary data
	result.Data = []map[string]interface{}{
		{
			"user":                username,
			"expectedPermissions": expectedUserPerms,
			"actualPermissions":   actualUserPerms,
			"createStatus":        createStatus,
			"readStatus":          readStatus,
			"updateStatus":        updateStatus,
			"deleteStatus":        deleteStatus,
		},
	}

	result.Passed = len(result.Issues) == 0
	return result, nil
}

// expandPermissions replicates server's permission expansion logic
func expandPermissions(rawPermsJSON string, entities []string) (map[string]interface{}, error) {
	var rawPerms map[string]string
	if err := json.Unmarshal([]byte(rawPermsJSON), &rawPerms); err != nil {
		return nil, fmt.Errorf("failed to parse raw permissions: %w", err)
	}

	entityPerms := make(map[string]string)

	for _, entity := range entities {
		perm := ""
		foundExplicit := false

		// Check for specific entity permission (case-insensitive)
		for key, value := range rawPerms {
			if strings.ToLower(key) == strings.ToLower(entity) {
				perm = value
				foundExplicit = true
				break
			}
		}

		// If no specific permission found, use wildcard
		if !foundExplicit {
			if wildcardPerm, ok := rawPerms["*"]; ok {
				perm = wildcardPerm
			}
		}

		// Only include entities with non-empty permissions
		if perm != "" {
			entityPerms[entity] = perm
		}
	}

	return map[string]interface{}{
		"entity":  entityPerms,
		"reports": []interface{}{},
	}, nil
}

// verifyPermissionsStructure validates actual permissions match expected expansion
func verifyPermissionsStructure(username string, actual map[string]interface{}, expected map[string]interface{}) []string {
	issues := []string{}

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

// getRoleIdFromBootstrapAuth looks up roleId for a username from bootstrap auth data
func getRoleIdFromBootstrapAuth(username string) (string, error) {
	for _, auth := range core.Auths {
		if auth["name"].(string) == username {
			return auth["roleId"].(string), nil
		}
	}
	return "", fmt.Errorf("username %s not found in bootstrap auth data", username)
}

// getPermissionsFromBootstrapRole looks up permissions JSON for a roleId from bootstrap role data
func getPermissionsFromBootstrapRole(roleId string) (string, error) {
	for _, role := range core.Roles {
		if role["id"].(string) == roleId {
			return role["permissions"].(string), nil
		}
	}
	return "", fmt.Errorf("roleId %s not found in bootstrap role data", roleId)
}
