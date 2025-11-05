package dynamic

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
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
	client := &http.Client{
		Timeout: 10 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}

	result := &types.TestResult{
		StatusCode: 200,
		Data:       []map[string]interface{}{},
		Issues:     []string{},
		Fields:     make(map[string][]interface{}),
		Passed:     false,
	}

	// Step 1: Login to get session cookie
	loginBody := map[string]interface{}{
		"login":    username,
		"password": password,
	}
	loginResp, loginRespBody, err := executeAuthRequest(client, "/api/login", "POST", loginBody, "")
	if err != nil {
		return result, fmt.Errorf("login failed: %w", err)
	}

	if loginResp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Login failed for %s: got %d", username, loginResp.StatusCode))
		return result, nil
	}

	// Extract session cookie
	var sessionID string
	for _, cookie := range loginResp.Cookies() {
		if cookie.Name == "sessionId" {
			sessionID = cookie.Value
			break
		}
	}

	if sessionID == "" {
		result.Issues = append(result.Issues, "No sessionId cookie received")
		return result, nil
	}

	// Extract permissions from login response
	var loginData map[string]interface{}
	var permissions string
	if err := json.Unmarshal(loginRespBody, &loginData); err == nil {
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
	hasCreate := strings.ContainsRune(permissions, 'c')
	createStatus := testOperation(client, "POST", "/api/User", sessionID, map[string]interface{}{
		"id":             "usr_authz_create_001",
		"username":       "authztest",
		"email":          "authz@test.com",
		"firstName":      "Authz",
		"lastName":       "Test",
		"gender":         "other",
		"dob":            "2000-01-01",
		"isAccountOwner": true,
		"netWorth":       50000,
	})
	checkPermission(result, "CREATE", hasCreate, createStatus)

	// Step 3: Test READ operation (r)
	hasRead := strings.ContainsRune(permissions, 'r')
	readStatus := testOperation(client, "GET", "/api/User/usr_get_001", sessionID, nil)
	checkPermission(result, "READ", hasRead, readStatus)

	// Step 4: Test UPDATE operation (u)
	hasUpdate := strings.ContainsRune(permissions, 'u')
	updateStatus := testOperation(client, "PUT", "/api/User/usr_update_001", sessionID, map[string]interface{}{
		"firstName": "Updated",
	})
	checkPermission(result, "UPDATE", hasUpdate, updateStatus)

	// Step 5: Test DELETE operation (d)
	hasDelete := strings.ContainsRune(permissions, 'd')
	deleteStatus := testOperation(client, "DELETE", "/api/User/usr_delete_002", sessionID, nil)
	checkPermission(result, "DELETE", hasDelete, deleteStatus)

	// Step 6: Test SEARCH operation (s)
	hasSearch := strings.ContainsRune(permissions, 's')
	searchStatus := testOperation(client, "GET", "/api/User", sessionID, nil)
	checkPermission(result, "SEARCH", hasSearch, searchStatus)

	// Step 7: Logout
	executeAuthRequest(client, "/api/logout", "POST", nil, sessionID)

	// Create summary data
	result.Data = []map[string]interface{}{
		{
			"user":         username,
			"permissions":  permissions,
			"createStatus": createStatus,
			"readStatus":   readStatus,
			"updateStatus": updateStatus,
			"deleteStatus": deleteStatus,
			"searchStatus": searchStatus,
		},
	}

	result.Passed = len(result.Issues) == 0
	return result, nil
}

// testOperation performs an HTTP operation and returns the status code
func testOperation(client *http.Client, method, path, sessionID string, body map[string]interface{}) int {
	var bodyReader io.Reader
	if body != nil {
		bodyBytes, _ := json.Marshal(body)
		bodyReader = bytes.NewReader(bodyBytes)
	}

	req, err := http.NewRequest(method, core.ServerURL+path, bodyReader)
	if err != nil {
		return 0
	}

	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	if sessionID != "" {
		req.AddCookie(&http.Cookie{
			Name:  "sessionId",
			Value: sessionID,
		})
	}

	resp, err := client.Do(req)
	if err != nil {
		return 0
	}
	defer resp.Body.Close()

	return resp.StatusCode
}

// checkPermission validates if the operation result matches expectations
func checkPermission(result *types.TestResult, operation string, hasPermission bool, actualStatus int) {
	var expectedStatus int
	if hasPermission {
		expectedStatus = 200
	} else {
		expectedStatus = 403
	}

	if actualStatus != expectedStatus {
		result.Issues = append(result.Issues, fmt.Sprintf("%s: expected %d, got %d", operation, expectedStatus, actualStatus))
	}
}
