package dynamic

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"validate/pkg/core"
)

// executeUrl executes an HTTP request and returns response and body
func executeUrl(url string, method string, body io.Reader) (*http.Response, []byte, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	req, err := http.NewRequest(method, url, body)
	if err != nil {
		return nil, nil, err
	}

	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	// Add session cookie if authenticated
	if core.SessionID != "" {
		req.Header.Set("Cookie", "sessionId="+core.SessionID)
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, nil, err
	}

	respBody, err := io.ReadAll(resp.Body)
	resp.Body.Close()
	if err != nil {
		return resp, nil, err
	}

	return resp, respBody, nil
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

// executeAuthRequest helper for auth endpoints with cookie handling
func executeAuthRequest(client *http.Client, path string, method string, body map[string]interface{}, sessionID string) (*http.Response, []byte, error) {
	url := core.ServerURL + path

	var bodyReader io.Reader
	if body != nil {
		bodyBytes, err := json.Marshal(body)
		if err != nil {
			return nil, nil, err
		}
		bodyReader = &jsonReader{data: bodyBytes}
	}

	req, err := http.NewRequest(method, url, bodyReader)
	if err != nil {
		return nil, nil, err
	}

	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	// Add session cookie if provided
	if sessionID != "" {
		req.AddCookie(&http.Cookie{
			Name:  "sessionId",
			Value: sessionID,
		})
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, nil, err
	}

	respBody, err := io.ReadAll(resp.Body)
	resp.Body.Close()
	if err != nil {
		return resp, nil, err
	}

	return resp, respBody, nil
}

// jsonReader wraps a byte slice to provide io.Reader interface
type jsonReader struct {
	data []byte
	pos  int
}

func (r *jsonReader) Read(p []byte) (n int, err error) {
	if r.pos >= len(r.data) {
		return 0, io.EOF
	}
	n = copy(p, r.data[r.pos:])
	r.pos += n
	return n, nil
}
