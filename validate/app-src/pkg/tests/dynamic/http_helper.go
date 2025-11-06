package dynamic

import (
	"net/http"

	"validate/pkg/core"
)

// ExecuteHTTP is a wrapper around core.ExecuteURL for dynamic tests
// that need to override the session ID per-request
//
// Parameters:
//   - path: API path (e.g., "/api/User" or "/api/login")
//   - method: HTTP method (GET, POST, PUT, DELETE)
//   - body: Optional request body (struct or map)
//   - sessionID: Optional session cookie value (overrides core.SessionID for this request)
//
// Returns:
//   - *http.Response: HTTP response object
//   - []byte: Response body bytes
//   - error: Any error that occurred
func ExecuteHTTP(path, method string, body interface{}, sessionID string) (*http.Response, []byte, error) {
	fullURL := core.ServerURL + path

	// Temporarily override core.SessionID for this request if sessionID is provided
	if sessionID != "" {
		oldSessionID := core.SessionID
		core.SessionID = sessionID
		defer func() { core.SessionID = oldSessionID }()
	}

	// Use the main HTTP executor with verbose logging
	return core.ExecuteURL(fullURL, method, body)
}

// ExecuteHTTPStatusOnly is a convenience wrapper that returns only the status code
// Useful for permission testing where we only care about 200/403/etc
func ExecuteHTTPStatusOnly(path, method string, body interface{}, sessionID string) int {
	resp, _, err := ExecuteHTTP(path, method, body, sessionID)
	if err != nil {
		return 0
	}
	return resp.StatusCode
}
