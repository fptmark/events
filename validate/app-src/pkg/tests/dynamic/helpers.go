package dynamic

import (
	"fmt"
	"net/http"
	"strings"

	"validate/pkg/core"
)

// LoginAs performs login and returns sessionID from cookie
// This is the single login helper used by all dynamic tests (auth, authz, etc.)
//
// Parameters:
//   - username: Login username
//   - password: Login password
//
// Returns:
//   - sessionID: Session cookie value (empty string if not found)
//   - resp: HTTP response object (for status code checking)
//   - body: Response body bytes (for further validation)
//   - error: Any error that occurred
func LoginAs(username, password string) (string, *http.Response, []byte, error) {
	loginBody := map[string]interface{}{
		"login":    username,
		"password": password,
	}

	resp, body, err := ExecuteHTTP("/api/login", "POST", loginBody, "")
	if err != nil {
		return "", nil, nil, err
	}

	// Extract session cookie
	var sessionID string
	for _, cookie := range resp.Cookies() {
		if cookie.Name == "sessionId" {
			sessionID = cookie.Value
			break
		}
	}

	return sessionID, resp, body, nil
}

// compareValues compares two values for sorting validation (respects core.CaseSensitive)
func compareValues(a, b interface{}) int {
	// Handle nil values
	if a == nil && b == nil {
		return 0
	}
	if a == nil {
		return -1
	}
	if b == nil {
		return 1
	}

	// Handle numeric values
	aNum, aIsNum := a.(float64)
	bNum, bIsNum := b.(float64)
	if aIsNum && bIsNum {
		if aNum < bNum {
			return -1
		}
		if aNum > bNum {
			return 1
		}
		return 0
	}

	// Handle string values with case sensitivity
	aStr := fmt.Sprintf("%v", a)
	bStr := fmt.Sprintf("%v", b)

	if core.CaseSensitive {
		return strings.Compare(aStr, bStr)
	}
	// Case-insensitive comparison
	return strings.Compare(strings.ToLower(aStr), strings.ToLower(bStr))
}
