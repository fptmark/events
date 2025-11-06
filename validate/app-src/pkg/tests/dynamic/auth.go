package dynamic

import (
	"encoding/json"
	"fmt"

	"validate/pkg/types"
)

// testAuth validates the complete Redis authentication workflow
func testAuth() (*types.TestResult, error) {
	result := &types.TestResult{
		StatusCode: 200,
		Data:       []map[string]interface{}{},
		Issues:     []string{},
		Fields:     make(map[string][]interface{}),
		Passed:     false,
	}

	// Step 1: Login with valid credentials
	sessionID, loginResp, loginRespBody, err := LoginAs("test_auth", "12345678")
	if err != nil {
		return result, fmt.Errorf("login request failed: %w", err)
	}

	if loginResp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Login failed: expected 200, got %d", loginResp.StatusCode))
		return result, nil
	}

	if sessionID == "" {
		result.Issues = append(result.Issues, "Login succeeded but no sessionId cookie returned")
		return result, nil
	}

	// Verify login response body (now uses standard format with status field)
	var loginData map[string]interface{}
	if err := json.Unmarshal(loginRespBody, &loginData); err != nil {
		result.Issues = append(result.Issues, "Login response is not valid JSON")
	} else {
		if status, ok := loginData["status"].(string); !ok || status != "success" {
			result.Issues = append(result.Issues, fmt.Sprintf("Login response status not 'success': got %v", status))
		}
	}

	// Step 2: Test refresh with session cookie
	refreshResp, refreshRespBody, err := ExecuteHTTP("/api/refresh", "POST", nil, sessionID)
	if err != nil {
		return result, fmt.Errorf("refresh request failed: %w", err)
	}

	if refreshResp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Refresh failed: expected 200, got %d", refreshResp.StatusCode))
	}

	var refreshData map[string]interface{}
	if err := json.Unmarshal(refreshRespBody, &refreshData); err != nil {
		result.Issues = append(result.Issues, "Refresh response is not valid JSON")
	} else {
		if status, ok := refreshData["status"].(string); !ok || status != "success" {
			result.Issues = append(result.Issues, fmt.Sprintf("Refresh response status not 'success': got %v", status))
		}
	}

	// Step 3: Logout with session cookie
	logoutResp, logoutRespBody, err := ExecuteHTTP("/api/logout", "POST", nil, sessionID)
	if err != nil {
		return result, fmt.Errorf("logout request failed: %w", err)
	}

	if logoutResp.StatusCode != 200 {
		result.Issues = append(result.Issues, fmt.Sprintf("Logout failed: expected 200, got %d", logoutResp.StatusCode))
	}

	var logoutData map[string]interface{}
	if err := json.Unmarshal(logoutRespBody, &logoutData); err != nil {
		result.Issues = append(result.Issues, "Logout response is not valid JSON")
	} else {
		if status, ok := logoutData["status"].(string); !ok || status != "success" {
			result.Issues = append(result.Issues, fmt.Sprintf("Logout response status not 'success': got %v", status))
		}
	}

	// Step 4: Try refresh after logout (should fail)
	postLogoutResp, postLogoutRespBody, err := ExecuteHTTP("/api/refresh", "POST", nil, sessionID)
	if err != nil {
		return result, fmt.Errorf("post-logout refresh request failed: %w", err)
	}

	// Check if refresh after logout fails (should return error status)
	var postLogoutData map[string]interface{}
	if err := json.Unmarshal(postLogoutRespBody, &postLogoutData); err != nil || postLogoutData == nil {
		// null response or invalid JSON is expected for failed refresh
	} else {
		if status, ok := postLogoutData["status"].(string); ok && status == "success" {
			result.Issues = append(result.Issues, "Refresh after logout should not return status='success'")
		}
	}

	// Step 5: Test invalid credentials
	_, badLoginResp, badLoginRespBody, err := LoginAs("test_auth", "wrongpassword")
	if err != nil {
		return result, fmt.Errorf("bad login request failed: %w", err)
	}

	// Check if login with invalid credentials fails (should return error status)
	var badLoginData map[string]interface{}
	if err := json.Unmarshal(badLoginRespBody, &badLoginData); err != nil || badLoginData == nil {
		// null response or invalid JSON is expected for failed login
	} else {
		if status, ok := badLoginData["status"].(string); ok && status == "success" {
			result.Issues = append(result.Issues, "Invalid credentials should not return status='success'")
		}
	}

	// Create summary data
	result.Data = []map[string]interface{}{
		{
			"loginStatus":          loginResp.StatusCode,
			"sessionIdReceived":    sessionID != "",
			"refreshStatus":        refreshResp.StatusCode,
			"logoutStatus":         logoutResp.StatusCode,
			"postLogoutStatus":     postLogoutResp.StatusCode,
			"badCredentialsStatus": badLoginResp.StatusCode,
		},
	}

	result.Passed = len(result.Issues) == 0
	return result, nil
}
